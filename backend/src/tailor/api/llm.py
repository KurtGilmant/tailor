from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel
from sqlmodel import col, select

from tailor.db import SessionDep
from tailor.llm import LLMGateway
from tailor.llm.guards import month_cloud_spend
from tailor.llm.models import LlmCall, LlmConsent, utcnow
from tailor.llm.secrets import api_key_for

router = APIRouter(prefix="/llm", tags=["llm"])


def get_gateway(request: Request) -> LLMGateway:
    return request.app.state.llm


GatewayDep = Annotated[LLMGateway, Depends(get_gateway)]


class ProviderStatus(BaseModel):
    name: str
    type: str
    is_cloud: bool
    api_key_configured: bool
    consent_granted_at: datetime | None


class RouteStatus(BaseModel):
    task: str
    provider: str
    model: str
    effort: str | None


class LlmStatus(BaseModel):
    mode: str
    monthly_budget_usd: float | None
    month_spend_usd: float
    providers: list[ProviderStatus]
    routes: list[RouteStatus]


class DailyUsage(BaseModel):
    day: date
    task: str
    calls: int
    input_tokens: int
    output_tokens: int
    cost_usd: float


class CallOut(BaseModel):
    id: int
    created_at: datetime
    task: str
    provider: str
    model: str
    prompt_id: str
    prompt_version: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    duration_ms: int
    status: str
    error: str | None


class LlmUsage(BaseModel):
    month_spend_usd: float
    monthly_budget_usd: float | None
    daily: list[DailyUsage]
    recent: list[CallOut]


def _provider_status(gateway: LLMGateway, session: SessionDep, name: str) -> ProviderStatus:
    config = gateway.config.providers[name]
    consent = session.get(LlmConsent, name)
    return ProviderStatus(
        name=name,
        type=config.type,
        is_cloud=config.is_cloud,
        api_key_configured=config.type == "fake" or api_key_for(name, config) is not None,
        consent_granted_at=consent.granted_at if consent else None,
    )


@router.get("/status")
def llm_status(gateway: GatewayDep, session: SessionDep) -> LlmStatus:
    config = gateway.config
    return LlmStatus(
        mode=config.mode,
        monthly_budget_usd=config.monthly_budget_usd,
        month_spend_usd=month_cloud_spend(session),
        providers=[_provider_status(gateway, session, name) for name in config.providers],
        routes=[
            RouteStatus(task=task.value, provider=r.provider, model=r.model, effort=r.effort)
            for task, r in config.routes.items()
        ],
    )


def _cloud_provider(gateway: LLMGateway, name: str) -> None:
    provider = gateway.config.providers.get(name)
    if provider is None:
        raise HTTPException(404, f"Fournisseur inconnu : « {name} ».")
    if not provider.is_cloud:
        raise HTTPException(400, f"« {name} » est local : aucun consentement n'est nécessaire.")


@router.post("/consents/{provider}", status_code=201)
def grant_consent(provider: str, gateway: GatewayDep, session: SessionDep) -> ProviderStatus:
    _cloud_provider(gateway, provider)
    if session.get(LlmConsent, provider) is None:
        session.add(LlmConsent(provider=provider))
        session.commit()
    return _provider_status(gateway, session, provider)


@router.delete("/consents/{provider}", status_code=204)
def revoke_consent(provider: str, gateway: GatewayDep, session: SessionDep) -> Response:
    _cloud_provider(gateway, provider)
    if consent := session.get(LlmConsent, provider):
        session.delete(consent)
        session.commit()
    return Response(status_code=204)


@router.get("/usage")
def llm_usage(
    gateway: GatewayDep,
    session: SessionDep,
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
) -> LlmUsage:
    since = utcnow() - timedelta(days=days)
    rows = session.exec(
        select(LlmCall).where(LlmCall.created_at >= since).order_by(col(LlmCall.id).desc())
    ).all()

    totals: dict[tuple[date, str], DailyUsage] = {}
    for row in rows:
        day = row.created_at.date()
        entry = totals.setdefault(
            (day, row.task),
            DailyUsage(
                day=day, task=row.task, calls=0, input_tokens=0, output_tokens=0, cost_usd=0
            ),
        )
        entry.calls += 1
        entry.input_tokens += row.input_tokens
        entry.output_tokens += row.output_tokens
        entry.cost_usd += row.cost_usd

    by_day: dict[date, list[DailyUsage]] = defaultdict(list)
    for (day, _task), entry in totals.items():
        by_day[day].append(entry)
    daily = [
        e for day in sorted(by_day, reverse=True) for e in sorted(by_day[day], key=lambda e: e.task)
    ]

    return LlmUsage(
        month_spend_usd=month_cloud_spend(session),
        monthly_budget_usd=gateway.config.monthly_budget_usd,
        daily=daily,
        recent=[CallOut.model_validate(row, from_attributes=True) for row in rows[:limit]],
    )
