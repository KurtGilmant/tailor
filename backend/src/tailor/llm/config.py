"""Configuration de la passerelle LLM : section [llm] de `tailor.toml`, fusionnée
avec les valeurs par défaut ci-dessous (voir `tailor.example.toml`)."""

from __future__ import annotations

from enum import StrEnum
from ipaddress import ip_address
from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, ValidationError, model_validator

from tailor.llm.errors import ConfigError

Effort = Literal["low", "medium", "high", "xhigh", "max"]


class Task(StrEnum):
    EXTRACT = "extract"  # CV -> faits, offre -> exigences
    SCORE = "score"  # couverture des exigences
    WRITE = "write"  # puces, accroche, lettre, réponses
    VERIFY = "verify"  # juge d'ancrage


class ProviderConfig(BaseModel):
    type: Literal["anthropic", "openai_compatible", "fake"]
    base_url: str | None = None
    # Variable d'environnement contenant la clé (sinon : trousseau macOS, puis SDK).
    api_key_env: str | None = None
    # Forcer le caractère cloud/local ; par défaut il est déduit du type et de l'URL.
    cloud: bool | None = None

    @property
    def is_cloud(self) -> bool:
        if self.cloud is not None:
            return self.cloud
        if self.type == "anthropic":
            return True
        if self.type == "fake":
            return False
        return not _is_loopback(self.base_url)


class RouteConfig(BaseModel):
    provider: str
    model: str
    effort: Effort | None = None
    max_tokens: int = Field(default=16000, gt=0)


class Price(BaseModel):
    """Tarif en dollars par million de jetons."""

    input: float = Field(ge=0)
    output: float = Field(ge=0)


DEFAULT_MODEL = "claude-opus-5-5"

DEFAULTS: dict[str, Any] = {
    "mode": "standard",
    "monthly_budget_usd": None,
    "max_attempts": 2,
    "providers": {
        "anthropic": {"type": "anthropic"},
        "ollama": {"type": "openai_compatible", "base_url": "http://localhost:11434/v1"},
    },
    "routes": {
        Task.EXTRACT: {"provider": "anthropic", "model": DEFAULT_MODEL, "effort": "low"},
        Task.SCORE: {"provider": "anthropic", "model": DEFAULT_MODEL, "effort": "medium"},
        Task.WRITE: {"provider": "anthropic", "model": DEFAULT_MODEL, "effort": "high"},
        Task.VERIFY: {"provider": "anthropic", "model": DEFAULT_MODEL, "effort": "high"},
    },
    # Tarifs Anthropic publics (API directe). Haiku 5.5 : tarif des prompts <= 100k jetons.
    "pricing": {
        "claude-opus-5-5": {"input": 4.0, "output": 20.0},
        "claude-sonnet-5-5": {"input": 2.0, "output": 10.0},
        "claude-haiku-5-5": {"input": 0.10, "output": 0.50},
    },
}


class LLMConfig(BaseModel):
    mode: Literal["standard", "local_strict"]
    monthly_budget_usd: float | None = Field(ge=0)
    max_attempts: int = Field(ge=1, le=5)
    providers: dict[str, ProviderConfig]
    routes: dict[Task, RouteConfig]
    pricing: dict[str, Price]

    @model_validator(mode="after")
    def _check_consistency(self) -> LLMConfig:
        for task, route in self.routes.items():
            provider = self.providers.get(route.provider)
            if provider is None:
                raise ValueError(f"tâche {task} : fournisseur inconnu « {route.provider} »")
            # Sans tarif, le plafond de dépenses ne pourrait pas être appliqué.
            if provider.is_cloud and route.model not in self.pricing:
                raise ValueError(f"tâche {task} : aucun tarif pour le modèle « {route.model} »")
        return self

    def cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        price = self.pricing.get(model)
        if price is None:
            return 0.0
        return (input_tokens * price.input + output_tokens * price.output) / 1_000_000

    @classmethod
    def from_raw(cls, raw: dict[str, Any] | None) -> LLMConfig:
        merged = _deep_merge(DEFAULTS, raw or {})
        try:
            return cls.model_validate(merged)
        except ValidationError as error:
            raise ConfigError(f"Section [llm] de tailor.toml invalide : {error}") from None


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _is_loopback(url: str | None) -> bool:
    host = urlparse(url or "").hostname or ""
    if host == "localhost":
        return True
    try:
        return ip_address(host).is_loopback
    except ValueError:
        return False
