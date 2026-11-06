"""Tables de la passerelle LLM : journal des appels, cache et consentements."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    # SQLModel stocke les datetime en UTC (type UTCDateTime) et exige un fuseau.
    return datetime.now(UTC)


class LlmCall(SQLModel, table=True):
    __tablename__ = "llm_call"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow, index=True)
    task: str
    provider: str
    model: str
    is_cloud: bool
    prompt_id: str
    prompt_version: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    duration_ms: int = 0
    # ok | cached | invalid (hors schéma) | refused | error | blocked (garde-fou)
    status: str
    error: str | None = None


class LlmCache(SQLModel, table=True):
    __tablename__ = "llm_cache"  # type: ignore[assignment]

    key: str = Field(primary_key=True)
    created_at: datetime = Field(default_factory=utcnow)
    model: str
    response_text: str


class LlmConsent(SQLModel, table=True):
    __tablename__ = "llm_consent"  # type: ignore[assignment]

    provider: str = Field(primary_key=True)
    granted_at: datetime = Field(default_factory=utcnow)
