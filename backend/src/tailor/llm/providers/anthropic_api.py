"""Adaptateur Anthropic (SDK officiel, endpoint beta pour les replis serveur).

- Sorties structurées : `output_config.format` (schéma JSON), revalidées par Pydantic.
- Profondeur : `output_config.effort` par tâche (ni `temperature` ni `thinking`,
  rejetés par les modèles récents).
- Refus : géré explicitement ; sur les modèles qui le supportent, `fallbacks: "default"`
  rejoue côté serveur une demande refusée sur le modèle de repli recommandé.
"""

from __future__ import annotations

from typing import Any

import anthropic

from tailor.llm.errors import ProviderError, RefusalError
from tailor.llm.providers.base import CloudGuard, Provider, ProviderReply, ProviderRequest

FALLBACK_BETA = "server-side-fallback-2026-07-01"
# Modèles acceptant `fallbacks: "default"` (Haiku 5.5 n'a pas de repli serveur).
FALLBACK_MODELS = frozenset(
    {"claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5", "claude-fable-5-1"}
)


class AnthropicProvider(Provider):
    def __init__(
        self,
        name: str,
        *,
        api_key: str | None,
        guard: CloudGuard | None,
        http_client: anthropic.DefaultAsyncHttpxClient | None = None,
    ) -> None:
        super().__init__(name, is_cloud=True, guard=guard)
        self._api_key = api_key
        self._http_client = http_client
        self._client: anthropic.AsyncAnthropic | None = None

    def _get_client(self) -> anthropic.AsyncAnthropic:
        # Créé à la demande : sans clé ni profil `ant auth login`, l'erreur n'apparaît
        # qu'au premier appel réel, pas au démarrage de l'application.
        if self._client is None:
            try:
                self._client = anthropic.AsyncAnthropic(
                    api_key=self._api_key, http_client=self._http_client, max_retries=2
                )
            except anthropic.AnthropicError:
                raise ProviderError(
                    f"Aucune clé pour « {self.name} » : définis ANTHROPIC_API_KEY ou "
                    "enregistre la clé dans le trousseau (voir README)."
                ) from None
        return self._client

    async def _generate(self, request: ProviderRequest) -> ProviderReply:
        output_config: dict[str, Any] = {
            "format": {"type": "json_schema", "schema": request.schema}
        }
        if request.effort:
            output_config["effort"] = request.effort
        extra: dict[str, Any] = {}
        if request.model in FALLBACK_MODELS:
            extra = {"betas": [FALLBACK_BETA], "fallbacks": "default"}

        try:
            message = await self._get_client().beta.messages.create(
                model=request.model,
                max_tokens=request.max_tokens,
                system=request.system,
                messages=[{"role": "user", "content": request.user}],
                output_config=output_config,  # type: ignore[arg-type]
                **extra,
            )
        # Messages volontairement pauvres : jamais d'en-têtes ni de corps de requête.
        except anthropic.APIStatusError as error:
            raise ProviderError(
                f"{self.name} a répondu {error.status_code} ({type(error).__name__})."
            ) from None
        except anthropic.APIConnectionError as error:
            raise ProviderError(f"{self.name} injoignable ({type(error).__name__}).") from None

        if message.stop_reason == "refusal":
            details = getattr(message, "stop_details", None)
            raise RefusalError(self.name, getattr(details, "category", None))
        if message.stop_reason == "max_tokens":
            raise ProviderError(
                f"Réponse tronquée par max_tokens ({request.max_tokens}) pour la tâche "
                f"« {request.task} »."
            )
        text = next((block.text for block in message.content if block.type == "text"), None)
        if text is None:
            raise ProviderError(f"{self.name} n'a renvoyé aucun bloc de texte.")
        return ProviderReply(
            text=text,
            model=message.model,
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
        )
