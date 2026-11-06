"""Garde-fous des appels cloud : mode local strict, consentement, plafond mensuel."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Engine, func
from sqlmodel import Session, col, select

from tailor.llm.config import LLMConfig
from tailor.llm.errors import BudgetExceeded, ConsentRequired, LocalStrictModeError
from tailor.llm.models import LlmCall, LlmConsent, utcnow
from tailor.llm.providers.base import CloudGuard, ProviderRequest


def month_start(now: datetime | None = None) -> datetime:
    now = now or utcnow()
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def month_cloud_spend(session: Session, now: datetime | None = None) -> float:
    total = session.exec(
        select(func.coalesce(func.sum(LlmCall.cost_usd), 0.0)).where(
            col(LlmCall.is_cloud).is_(True), LlmCall.created_at >= month_start(now)
        )
    ).one()
    return float(total)


def make_cloud_guard(engine: Engine, config: LLMConfig) -> CloudGuard:
    def guard(provider: str, request: ProviderRequest) -> None:
        if config.mode == "local_strict":
            raise LocalStrictModeError(request.task, provider)
        with Session(engine) as session:
            if session.get(LlmConsent, provider) is None:
                raise ConsentRequired(provider)
            budget = config.monthly_budget_usd
            if budget is not None:
                spent = month_cloud_spend(session)
                if spent >= budget:
                    raise BudgetExceeded(spent, budget)

    return guard
