"""Passerelle LLM : point d'entrée unique de toutes les fonctionnalités vers les modèles.

    result = await gateway.complete(Task.EXTRACT, "offer-requirements", {"offer": text}, Reqs)

Elle choisit le fournisseur et le modèle selon la tâche, rend le prompt versionné,
sert le cache, revalide la réponse avec Pydantic (avec relance sur erreur), et
journalise chaque appel. Les garde-fous cloud sont appliqués dans les adaptateurs.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Mapping
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError
from sqlalchemy import Engine
from sqlmodel import Session

from tailor.llm.config import LLMConfig, Task
from tailor.llm.errors import (
    CloudCallBlocked,
    ConfigError,
    ProviderError,
    RefusalError,
    SchemaValidationError,
)
from tailor.llm.guards import make_cloud_guard
from tailor.llm.models import LlmCache, LlmCall
from tailor.llm.prompts import PromptLibrary, RenderedPrompt
from tailor.llm.providers.anthropic_api import AnthropicProvider
from tailor.llm.providers.base import Provider, ProviderReply, ProviderRequest
from tailor.llm.providers.fake import FakeProvider
from tailor.llm.providers.openai_compat import OpenAICompatProvider
from tailor.llm.schema import strict_schema
from tailor.llm.secrets import api_key_for

T = TypeVar("T", bound=BaseModel)

RETRY_TEMPLATE = """Ta réponse précédente ne respectait pas le schéma attendu.
Erreurs de validation :
{errors}

Réponse précédente :
<<<
{previous}
>>>

Réponds de nouveau à la demande ci-dessous en respectant strictement le schéma.

{user}"""


class LLMGateway:
    def __init__(
        self,
        *,
        engine: Engine,
        config: LLMConfig,
        prompts: PromptLibrary,
        providers: Mapping[str, Provider],
    ) -> None:
        self.engine = engine
        self.config = config
        self.prompts = prompts
        self.providers = dict(providers)

    @classmethod
    def from_config(
        cls, engine: Engine, config: LLMConfig, prompts: PromptLibrary | None = None
    ) -> LLMGateway:
        guard = make_cloud_guard(engine, config)
        providers: dict[str, Provider] = {}
        for name, provider in config.providers.items():
            cloud_guard = guard if provider.is_cloud else None
            if provider.type == "anthropic":
                providers[name] = AnthropicProvider(
                    name, api_key=api_key_for(name, provider), guard=cloud_guard
                )
            elif provider.type == "openai_compatible":
                if not provider.base_url:
                    raise ConfigError(f"Fournisseur « {name} » : base_url obligatoire.")
                providers[name] = OpenAICompatProvider(
                    name,
                    base_url=provider.base_url,
                    api_key=api_key_for(name, provider),
                    is_cloud=provider.is_cloud,
                    guard=cloud_guard,
                )
            else:
                providers[name] = FakeProvider(
                    name,
                    is_cloud=provider.is_cloud,
                    guard=cloud_guard,
                    replies_dir=Path(provider.replies_dir) if provider.replies_dir else None,
                )
        return cls(
            engine=engine, config=config, prompts=prompts or PromptLibrary(), providers=providers
        )

    async def complete(
        self,
        task: Task,
        prompt_id: str,
        inputs: Mapping[str, str],
        schema: type[T],
        *,
        regenerate: bool = False,
    ) -> T:
        route = self.config.routes[task]
        provider = self.providers[route.provider]
        prompt = self.prompts.get(prompt_id).render(inputs)
        json_schema = strict_schema(schema)
        key = _cache_key(route.provider, route.model, route.effort, prompt, json_schema)

        if not regenerate and (cached := self._cached(key, schema)) is not None:
            self._log(task, provider, route.model, prompt, status="cached")
            return cached

        user, last_error = prompt.user, ""
        for _attempt in range(self.config.max_attempts):
            request = ProviderRequest(
                task=task.value,
                prompt_id=prompt_id,
                model=route.model,
                system=prompt.system,
                user=user,
                schema=json_schema,
                schema_name=schema.__name__,
                effort=route.effort,
                max_tokens=route.max_tokens,
            )
            started = time.perf_counter()
            try:
                reply = await provider.generate(request)
            except CloudCallBlocked as error:
                self._log(task, provider, route.model, prompt, status="blocked", error=error)
                raise
            except RefusalError as error:
                self._log(task, provider, route.model, prompt, status="refused", error=error)
                raise
            except ProviderError as error:
                self._log(task, provider, route.model, prompt, status="error", error=error)
                raise
            duration_ms = int((time.perf_counter() - started) * 1000)

            try:
                parsed = schema.model_validate_json(reply.text)
            except ValidationError as error:
                last_error = _summarize(error)
                self._log(
                    task,
                    provider,
                    route.model,
                    prompt,
                    status="invalid",
                    error=last_error,
                    reply=reply,
                    duration_ms=duration_ms,
                )
                user = RETRY_TEMPLATE.format(
                    errors=last_error, previous=reply.text, user=prompt.user
                )
                continue

            self._log(
                task,
                provider,
                route.model,
                prompt,
                status="ok",
                reply=reply,
                duration_ms=duration_ms,
            )
            self._store(key, reply)
            return parsed

        raise SchemaValidationError(
            task.value, schema.__name__, self.config.max_attempts, last_error
        )

    def _cached(self, key: str, schema: type[T]) -> T | None:
        with Session(self.engine) as session:
            entry = session.get(LlmCache, key)
        if entry is None:
            return None
        try:
            return schema.model_validate_json(entry.response_text)
        except ValidationError:
            return None  # schéma modifié depuis : on régénère

    def _store(self, key: str, reply: ProviderReply) -> None:
        with Session(self.engine) as session:
            session.merge(LlmCache(key=key, model=reply.model, response_text=reply.text))
            session.commit()

    def _log(
        self,
        task: Task,
        provider: Provider,
        model: str,
        prompt: RenderedPrompt,
        *,
        status: str,
        error: Exception | str | None = None,
        reply: ProviderReply | None = None,
        duration_ms: int = 0,
    ) -> None:
        served_model = reply.model if reply else model
        input_tokens = reply.input_tokens if reply else 0
        output_tokens = reply.output_tokens if reply else 0
        cost = 0.0
        if provider.is_cloud and reply is not None:
            # Le modèle servi peut différer (repli serveur) : on facture au tarif servi.
            pricing_model = served_model if served_model in self.config.pricing else model
            cost = self.config.cost(pricing_model, input_tokens, output_tokens)
        row = LlmCall(
            task=task.value,
            provider=provider.name,
            model=served_model,
            is_cloud=provider.is_cloud,
            prompt_id=prompt.prompt_id,
            prompt_version=prompt.version,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            duration_ms=duration_ms,
            status=status,
            error=str(error) if error else None,
        )
        with Session(self.engine) as session:
            session.add(row)
            session.commit()


def _cache_key(
    provider: str, model: str, effort: str | None, prompt: RenderedPrompt, schema: dict
) -> str:
    parts = [provider, model, effort, prompt.prompt_id, prompt.version, prompt.system, prompt.user]
    payload = json.dumps([*parts, schema], sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _summarize(error: ValidationError, limit: int = 5) -> str:
    lines = [
        f"- {'.'.join(str(p) for p in item['loc']) or '(racine)'} : {item['msg']}"
        for item in error.errors(include_url=False)[:limit]
    ]
    return "\n".join(lines)
