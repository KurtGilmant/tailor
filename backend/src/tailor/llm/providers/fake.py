"""Faux fournisseur déterministe : tests, et développement sans dépenser un centime.

Avec des réponses scriptées, il les rend dans l'ordre. Sans script, il fabrique une
instance minimale valide du schéma demandé (utile pour faire tourner l'interface).
"""

from __future__ import annotations

import json
from collections import deque
from collections.abc import Callable, Iterable
from typing import Any

from tailor.llm.errors import ProviderError
from tailor.llm.providers.base import CloudGuard, Provider, ProviderReply, ProviderRequest

Reply = str | Callable[[ProviderRequest], str]


class FakeProvider(Provider):
    def __init__(
        self,
        name: str = "fake",
        replies: Iterable[Reply] | None = None,
        *,
        is_cloud: bool = False,
        guard: CloudGuard | None = None,
        tokens: tuple[int, int] = (100, 50),
    ) -> None:
        super().__init__(name, is_cloud=is_cloud, guard=guard)
        self._scripted = replies is not None
        self._replies: deque[Reply] = deque(replies or [])
        self._tokens = tokens
        self.requests: list[ProviderRequest] = []

    async def _generate(self, request: ProviderRequest) -> ProviderReply:
        self.requests.append(request)
        if self._scripted:
            if not self._replies:
                raise ProviderError(f"Faux fournisseur « {self.name} » : plus de réponse scriptée.")
            reply = self._replies.popleft()
            text = reply(request) if callable(reply) else reply
        else:
            text = json.dumps(example_from_schema(request.schema), ensure_ascii=False)
        return ProviderReply(text, request.model, *self._tokens)


def example_from_schema(schema: dict[str, Any], root: dict[str, Any] | None = None) -> Any:
    root = root or schema
    if "$ref" in schema:
        name = schema["$ref"].rsplit("/", 1)[-1]
        return example_from_schema(root.get("$defs", {})[name], root)
    if "enum" in schema:
        return schema["enum"][0]
    if "const" in schema:
        return schema["const"]
    for key in ("anyOf", "oneOf"):
        if key in schema:
            options = [s for s in schema[key] if s.get("type") != "null"] or schema[key]
            return example_from_schema(options[0], root)
    kind = schema.get("type")
    if kind == "object":
        return {
            name: example_from_schema(sub, root)
            for name, sub in schema.get("properties", {}).items()
        }
    if kind == "array":
        return []
    return {"string": "exemple", "integer": 0, "number": 0.0, "boolean": False}.get(kind or "")
