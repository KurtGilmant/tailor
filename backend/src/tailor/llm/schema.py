"""Conversion d'un modèle Pydantic en schéma JSON « strict » pour les sorties structurées.

Les sorties structurées des fournisseurs exigent des objets fermés
(`additionalProperties: false`) dont toutes les propriétés sont requises. Pydantic
revalide de toute façon la réponse : ce schéma sert à contraindre la génération.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

_SCHEMA_MAPS = ("properties", "$defs", "definitions")
_SCHEMA_LISTS = ("anyOf", "oneOf", "allOf", "prefixItems")
_SCHEMA_SINGLE = ("items", "additionalProperties", "not")


def strict_schema(model: type[BaseModel]) -> dict[str, Any]:
    schema = model.model_json_schema()
    _tighten(schema)
    return schema


def _tighten(node: dict[str, Any]) -> None:
    # On ne parcourt que des positions de sous-schémas : une propriété nommée
    # « default » dans `properties` ne doit pas être prise pour le mot-clé `default`.
    node.pop("default", None)
    if node.get("type") == "object" and "properties" in node:
        node["additionalProperties"] = False
        node["required"] = list(node["properties"])
    for key in _SCHEMA_MAPS:
        for child in node.get(key, {}).values():
            _tighten(child)
    for key in _SCHEMA_LISTS:
        for child in node.get(key, []):
            _tighten(child)
    for key in _SCHEMA_SINGLE:
        child = node.get(key)
        if isinstance(child, dict):
            _tighten(child)
