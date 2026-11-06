"""Garde-fous cloud (spec llm-gateway) : chacun bloque l'appel AVANT tout trafic réseau."""

import asyncio
from datetime import timedelta

import anthropic
import httpx2
import pytest
from sqlalchemy import Engine
from sqlmodel import Session

from tailor.llm import LLMGateway, Task
from tailor.llm.errors import BudgetExceeded, ConsentRequired, LocalStrictModeError
from tailor.llm.guards import make_cloud_guard, month_cloud_spend
from tailor.llm.models import LlmCall, LlmConsent, utcnow
from tailor.llm.prompts import PromptLibrary
from tailor.llm.providers.anthropic_api import AnthropicProvider
from tailor.llm.providers.fake import FakeProvider

from .conftest import Person, llm_config

CLOUD_ROUTE = {"extract": {"provider": "anthropic", "model": "claude-opus-5-5"}}


class NetworkSpy:
    def __init__(self) -> None:
        self.requests = 0

    def __call__(self, _req: httpx2.Request) -> httpx2.Response:
        self.requests += 1
        return httpx2.Response(500)


def cloud_gateway(
    engine: Engine, prompts: PromptLibrary, spy: NetworkSpy, **cfg: object
) -> LLMGateway:
    config = llm_config(routes=CLOUD_ROUTE, **cfg)
    client = anthropic.DefaultAsyncHttpxClient(transport=httpx2.MockTransport(spy))
    provider = AnthropicProvider(
        "anthropic", api_key="k", guard=make_cloud_guard(engine, config), http_client=client
    )
    return LLMGateway(
        engine=engine, config=config, prompts=prompts, providers={"anthropic": provider}
    )


def complete(gw: LLMGateway) -> Person:
    return asyncio.run(gw.complete(Task.EXTRACT, "demo", {"text": "x"}, Person))


def consent(engine: Engine) -> None:
    with Session(engine) as session:
        session.add(LlmConsent(provider="anthropic"))
        session.commit()


def spend(engine: Engine, amount: float, *, days_ago: int = 0) -> None:
    with Session(engine) as session:
        session.add(
            LlmCall(
                created_at=utcnow() - timedelta(days=days_ago),
                task="write",
                provider="anthropic",
                model="claude-opus-5-5",
                is_cloud=True,
                prompt_id="p",
                prompt_version="1",
                cost_usd=amount,
                status="ok",
            )
        )
        session.commit()


def test_consent_required_before_first_cloud_call(engine: Engine, prompts: PromptLibrary) -> None:
    spy = NetworkSpy()
    with pytest.raises(ConsentRequired, match="anthropic"):
        complete(cloud_gateway(engine, prompts, spy))
    assert spy.requests == 0


def test_local_strict_blocks_cloud_even_with_consent(
    engine: Engine, prompts: PromptLibrary
) -> None:
    consent(engine)
    spy = NetworkSpy()
    with pytest.raises(LocalStrictModeError, match="extract"):
        complete(cloud_gateway(engine, prompts, spy, mode="local_strict"))
    assert spy.requests == 0


def test_budget_reached_blocks_cloud(engine: Engine, prompts: PromptLibrary) -> None:
    consent(engine)
    spend(engine, 6.0)
    spend(engine, 4.5)
    spy = NetworkSpy()
    with pytest.raises(BudgetExceeded, match=r"10\.50 \$ consommés pour un plafond de 10\.00"):
        complete(cloud_gateway(engine, prompts, spy, monthly_budget_usd=10.0))
    assert spy.requests == 0


def test_under_budget_with_consent_reaches_network(engine: Engine, prompts: PromptLibrary) -> None:
    consent(engine)
    spend(engine, 2.0)
    spy = NetworkSpy()
    with pytest.raises(Exception):  # noqa: B017  (le faux serveur répond 500)
        complete(cloud_gateway(engine, prompts, spy, monthly_budget_usd=10.0))
    assert spy.requests > 0


def test_month_spend_ignores_previous_months_and_local_calls(engine: Engine) -> None:
    spend(engine, 3.0)
    spend(engine, 99.0, days_ago=40)
    with Session(engine) as session:
        session.add(
            LlmCall(
                task="extract",
                provider="ollama",
                model="m",
                is_cloud=False,
                prompt_id="p",
                prompt_version="1",
                cost_usd=50.0,
                status="ok",
            )
        )
        session.commit()
        assert month_cloud_spend(session) == pytest.approx(3.0)


def test_local_provider_is_never_guarded(engine: Engine, prompts: PromptLibrary) -> None:
    """Le mode local strict et l'absence de consentement n'affectent pas un modèle local."""
    config = llm_config(mode="local_strict")
    local = FakeProvider(replies=['{"name": "Jean", "age": 1}'])
    gw = LLMGateway(engine=engine, config=config, prompts=prompts, providers={"fake": local})
    assert complete(gw).name == "Jean"


def test_blocked_call_is_journaled(engine: Engine, prompts: PromptLibrary) -> None:
    with pytest.raises(ConsentRequired):
        complete(cloud_gateway(engine, prompts, NetworkSpy()))
    with Session(engine) as session:
        row = session.get(LlmCall, 1)
    assert row is not None and row.status == "blocked" and row.cost_usd == 0
