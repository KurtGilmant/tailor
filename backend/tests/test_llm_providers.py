"""Adaptateurs Anthropic et compatible OpenAI, testés sans réseau via httpx2.MockTransport
(les deux SDK reposent sur httpx2). Les tests d'intégration réels sont ignorés par défaut."""

import asyncio
import json
import logging
import socket
from collections.abc import Callable

import anthropic
import httpx2
import openai
import pytest
from sqlalchemy import Engine
from sqlmodel import Session, select

from tailor.llm import LLMGateway, Task
from tailor.llm.errors import ProviderError, RefusalError
from tailor.llm.models import LlmCall, LlmConsent
from tailor.llm.prompts import PromptLibrary
from tailor.llm.providers.anthropic_api import FALLBACK_BETA, AnthropicProvider
from tailor.llm.providers.base import ProviderRequest
from tailor.llm.providers.openai_compat import OpenAICompatProvider

from .conftest import REAL_ANTHROPIC_KEY, Person, llm_config

FAKE_KEY = "sk-ant-api03-NE-JAMAIS-JOURNALISER"
Handler = Callable[[httpx2.Request], httpx2.Response]


def request(model: str = "claude-opus-5-5", effort: str | None = "low") -> ProviderRequest:
    return ProviderRequest(
        task="extract",
        model=model,
        system="sys",
        user="usr",
        schema={"type": "object"},
        schema_name="Person",
        effort=effort,
        max_tokens=1000,
    )


def anthropic_message(text: str = '{"name": "Jean", "age": 32}', **extra: object) -> dict:
    return {
        "id": "msg_1",
        "type": "message",
        "role": "assistant",
        "model": "claude-opus-5-5",
        "content": [{"type": "text", "text": text}],
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {"input_tokens": 12, "output_tokens": 7},
        **extra,
    }


def anthropic_provider(handler: Handler, *, guard=lambda *_: None) -> AnthropicProvider:
    client = anthropic.DefaultAsyncHttpxClient(transport=httpx2.MockTransport(handler))
    return AnthropicProvider("anthropic", api_key=FAKE_KEY, guard=guard, http_client=client)


def test_anthropic_request_shape_and_reply() -> None:
    seen: list[httpx2.Request] = []

    def handler(req: httpx2.Request) -> httpx2.Response:
        seen.append(req)
        return httpx2.Response(200, json=anthropic_message())

    reply = asyncio.run(anthropic_provider(handler).generate(request()))

    assert (reply.text, reply.model, reply.input_tokens, reply.output_tokens) == (
        '{"name": "Jean", "age": 32}',
        "claude-opus-5-5",
        12,
        7,
    )
    body = json.loads(seen[0].content)
    assert body["output_config"] == {
        "format": {"type": "json_schema", "schema": {"type": "object"}},
        "effort": "low",
    }
    assert body["fallbacks"] == "default"
    assert FALLBACK_BETA in seen[0].headers["anthropic-beta"]
    assert "temperature" not in body and "thinking" not in body  # rejetés par les modèles récents
    assert body["system"] == "sys"
    assert body["messages"] == [{"role": "user", "content": "usr"}]


def test_anthropic_no_fallback_for_haiku() -> None:
    seen: list[httpx2.Request] = []

    def handler(req: httpx2.Request) -> httpx2.Response:
        seen.append(req)
        return httpx2.Response(200, json=anthropic_message())

    asyncio.run(
        anthropic_provider(handler).generate(request(model="claude-haiku-5-5", effort=None))
    )
    body = json.loads(seen[0].content)
    assert "fallbacks" not in body
    assert "effort" not in body["output_config"]


def test_anthropic_refusal() -> None:
    def handler(_req: httpx2.Request) -> httpx2.Response:
        message = anthropic_message(stop_details={"type": "refusal", "category": "cyber"})
        message.update(content=[], stop_reason="refusal")
        return httpx2.Response(200, json=message)

    with pytest.raises(RefusalError, match="cyber"):
        asyncio.run(anthropic_provider(handler).generate(request()))


def test_anthropic_truncated_reply() -> None:
    def handler(_req: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, json=anthropic_message(stop_reason="max_tokens"))

    with pytest.raises(ProviderError, match="tronquée"):
        asyncio.run(anthropic_provider(handler).generate(request()))


def test_api_key_never_logged(
    engine: Engine, prompts: PromptLibrary, caplog: pytest.LogCaptureFixture
) -> None:
    def handler(req: httpx2.Request) -> httpx2.Response:
        assert req.headers["x-api-key"] == FAKE_KEY  # la clé part bien… vers l'API seulement
        error = {"type": "error", "error": {"type": "authentication_error", "message": "bad key"}}
        return httpx2.Response(401, json=error)

    with Session(engine) as session:
        session.add(LlmConsent(provider="anthropic"))
        session.commit()
    config = llm_config(routes={"extract": {"provider": "anthropic", "model": "claude-opus-5-5"}})
    gw = LLMGateway(
        engine=engine,
        config=config,
        prompts=prompts,
        providers={"anthropic": anthropic_provider(handler)},
    )

    caplog.set_level(logging.DEBUG)
    with pytest.raises(ProviderError) as raised:
        asyncio.run(gw.complete(Task.EXTRACT, "demo", {"text": "x"}, Person))

    assert FAKE_KEY not in str(raised.value)
    assert FAKE_KEY not in caplog.text
    with Session(engine) as session:
        rows = session.exec(select(LlmCall)).all()
    assert rows and all(FAKE_KEY not in (row.error or "") for row in rows)


def openai_completion(content: str, finish_reason: str = "stop") -> dict:
    return {
        "id": "c1",
        "object": "chat.completion",
        "created": 0,
        "model": "qwen-local",
        "choices": [
            {
                "index": 0,
                "finish_reason": finish_reason,
                "message": {"role": "assistant", "content": content},
            }
        ],
        "usage": {"prompt_tokens": 9, "completion_tokens": 4, "total_tokens": 13},
    }


def openai_provider(handler: Handler) -> OpenAICompatProvider:
    client = openai.DefaultAsyncHttpxClient(transport=httpx2.MockTransport(handler))
    return OpenAICompatProvider(
        "ollama",
        base_url="http://localhost:11434/v1",
        api_key=None,
        is_cloud=False,
        guard=None,
        http_client=client,
    )


def test_openai_compat_request_shape_and_reply() -> None:
    seen: list[httpx2.Request] = []

    def handler(req: httpx2.Request) -> httpx2.Response:
        seen.append(req)
        return httpx2.Response(200, json=openai_completion('{"name": "Jean", "age": 32}'))

    reply = asyncio.run(openai_provider(handler).generate(request(model="qwen-local")))

    assert seen[0].url.path == "/v1/chat/completions"
    body = json.loads(seen[0].content)
    assert body["response_format"]["type"] == "json_schema"
    assert body["response_format"]["json_schema"]["name"] == "Person"
    assert body["response_format"]["json_schema"]["strict"] is True
    assert [m["role"] for m in body["messages"]] == ["system", "user"]
    assert (reply.input_tokens, reply.output_tokens, reply.model) == (9, 4, "qwen-local")


def test_openai_compat_truncated_and_unreachable() -> None:
    def truncated(_req: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, json=openai_completion("{", finish_reason="length"))

    with pytest.raises(ProviderError, match="tronquée"):
        asyncio.run(openai_provider(truncated).generate(request()))

    def down(req: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("refusé", request=req)

    with pytest.raises(ProviderError, match="injoignable"):
        asyncio.run(openai_provider(down).generate(request()))


def _ollama_running() -> bool:
    try:
        socket.create_connection(("127.0.0.1", 11434), timeout=0.3).close()
    except OSError:
        return False
    return True


@pytest.mark.integration
@pytest.mark.skipif(not REAL_ANTHROPIC_KEY, reason="ANTHROPIC_API_KEY absente")
def test_integration_anthropic(engine: Engine, prompts: PromptLibrary) -> None:
    with Session(engine) as session:
        session.add(LlmConsent(provider="anthropic"))
        session.commit()
    provider = AnthropicProvider("anthropic", api_key=REAL_ANTHROPIC_KEY, guard=lambda *_: None)
    config = llm_config(
        routes={"extract": {"provider": "anthropic", "model": "claude-opus-5-5", "effort": "low"}}
    )
    gw = LLMGateway(
        engine=engine, config=config, prompts=prompts, providers={"anthropic": provider}
    )
    result = asyncio.run(gw.complete(Task.EXTRACT, "demo", {"text": "Jean a 32 ans."}, Person))
    assert result == Person(name="Jean", age=32)


@pytest.mark.integration
@pytest.mark.skipif(not _ollama_running(), reason="Ollama ne tourne pas sur :11434")
def test_integration_ollama(engine: Engine, prompts: PromptLibrary) -> None:
    import os

    model = os.environ.get("TAILOR_OLLAMA_MODEL", "qwen3:8b")
    provider = OpenAICompatProvider(
        "ollama", base_url="http://localhost:11434/v1", api_key=None, is_cloud=False, guard=None
    )
    config = llm_config(routes={"extract": {"provider": "ollama", "model": model}})
    gw = LLMGateway(engine=engine, config=config, prompts=prompts, providers={"ollama": provider})
    result = asyncio.run(gw.complete(Task.EXTRACT, "demo", {"text": "Jean a 32 ans."}, Person))
    assert result.age == 32
