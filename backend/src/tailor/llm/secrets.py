"""Lecture des clés d'API : variable d'environnement, puis trousseau de l'OS.

Pour enregistrer une clé dans le trousseau macOS :
    uv run python -m keyring set tailor anthropic
"""

from __future__ import annotations

import os

import keyring
from keyring.errors import KeyringError

from tailor.llm.config import ProviderConfig

KEYRING_SERVICE = "tailor"
DEFAULT_ENV = {"anthropic": "ANTHROPIC_API_KEY"}


def api_key_for(name: str, provider: ProviderConfig) -> str | None:
    env_var = provider.api_key_env or DEFAULT_ENV.get(provider.type)
    if env_var and (value := os.environ.get(env_var)):
        return value
    try:
        return keyring.get_password(KEYRING_SERVICE, name)
    except KeyringError:
        return None
