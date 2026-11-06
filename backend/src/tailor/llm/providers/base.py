from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProviderRequest:
    task: str
    prompt_id: str
    model: str
    system: str
    user: str
    schema: dict[str, Any]
    schema_name: str
    effort: str | None
    max_tokens: int


@dataclass(frozen=True)
class ProviderReply:
    text: str
    model: str
    input_tokens: int
    output_tokens: int


# Vérifie consentement, mode local strict et plafond ; lève CloudCallBlocked sinon.
CloudGuard = Callable[[str, ProviderRequest], None]


class Provider(ABC):
    """Fournisseur de modèles. Un fournisseur cloud consulte son garde-fou AVANT tout
    trafic réseau : c'est l'adaptateur lui-même qui refuse, pas l'appelant."""

    def __init__(self, name: str, *, is_cloud: bool, guard: CloudGuard | None = None) -> None:
        self.name = name
        self.is_cloud = is_cloud
        self._guard = guard

    async def generate(self, request: ProviderRequest) -> ProviderReply:
        if self.is_cloud:
            if self._guard is None:
                raise RuntimeError(f"Fournisseur cloud « {self.name} » sans garde-fou.")
            self._guard(self.name, request)
        return await self._generate(request)

    @abstractmethod
    async def _generate(self, request: ProviderRequest) -> ProviderReply: ...
