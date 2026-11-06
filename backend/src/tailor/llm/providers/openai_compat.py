"""Adaptateur pour tout serveur compatible avec l'API OpenAI Chat Completions
(Ollama, LM Studio, vLLM…), utilisé pour le mode local."""

from __future__ import annotations

import openai

from tailor.llm.errors import ProviderError, RefusalError
from tailor.llm.providers.base import CloudGuard, Provider, ProviderReply, ProviderRequest


class OpenAICompatProvider(Provider):
    def __init__(
        self,
        name: str,
        *,
        base_url: str,
        api_key: str | None,
        is_cloud: bool,
        guard: CloudGuard | None,
        http_client: openai.DefaultAsyncHttpxClient | None = None,
    ) -> None:
        super().__init__(name, is_cloud=is_cloud, guard=guard)
        # Les serveurs locaux ignorent la clé mais le SDK en exige une.
        self._client = openai.AsyncOpenAI(
            api_key=api_key or "local",
            base_url=base_url,
            http_client=http_client,
            max_retries=1,
        )

    async def _generate(self, request: ProviderRequest) -> ProviderReply:
        try:
            completion = await self._client.chat.completions.create(
                model=request.model,
                max_tokens=request.max_tokens,
                messages=[
                    {"role": "system", "content": request.system},
                    {"role": "user", "content": request.user},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": request.schema_name,
                        "schema": request.schema,
                        "strict": True,
                    },
                },
            )
        except openai.APIStatusError as error:
            raise ProviderError(
                f"{self.name} a répondu {error.status_code} ({type(error).__name__})."
            ) from None
        except openai.APIConnectionError as error:
            raise ProviderError(f"{self.name} injoignable ({type(error).__name__}).") from None

        if not completion.choices:
            raise ProviderError(f"{self.name} n'a renvoyé aucun choix.")
        choice = completion.choices[0]
        if getattr(choice.message, "refusal", None):
            raise RefusalError(self.name, None)
        if choice.finish_reason == "length":
            raise ProviderError(
                f"Réponse tronquée par max_tokens ({request.max_tokens}) pour la tâche "
                f"« {request.task} »."
            )
        if not choice.message.content:
            raise ProviderError(f"{self.name} a renvoyé une réponse vide.")
        usage = completion.usage
        return ProviderReply(
            text=choice.message.content,
            model=completion.model or request.model,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
        )
