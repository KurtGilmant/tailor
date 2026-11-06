"""Sécurité de l'application locale (design D12).

L'application n'écoute que sur la boucle locale, mais une page web malveillante peut
quand même viser `localhost` depuis le navigateur. Trois verrous, dans cet ordre :

1. en-tête `Host` limité à 127.0.0.1/localhost sur le bon port (anti DNS rebinding) ;
2. en-tête `Origin`, quand il est présent, limité aux origines connues (anti CSRF) ;
3. jeton `Authorization: Bearer` obligatoire sur toutes les routes `/api`.
"""

from __future__ import annotations

import secrets
from collections.abc import Iterable
from pathlib import Path

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

LOOPBACK_NAMES = ("127.0.0.1", "localhost")
DEV_WEB_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")


def allowed_hosts(port: int) -> frozenset[str]:
    return frozenset(f"{name}:{port}" for name in LOOPBACK_NAMES)


def allowed_origins(port: int, *, dev: bool) -> frozenset[str]:
    origins = {f"http://{host}" for host in allowed_hosts(port)}
    if dev:
        origins.update(DEV_WEB_ORIGINS)
    return frozenset(origins)


def new_token() -> str:
    return secrets.token_urlsafe(32)


def dev_token(home: Path) -> str:
    """En dev, le jeton survit aux rechargements du serveur pour ne pas casser le front."""
    path = home / "dev_token"
    if path.exists():
        return path.read_text().strip()
    token = new_token()
    path.write_text(token)
    path.chmod(0o600)
    return token


def _reject(status: int, detail: str) -> JSONResponse:
    return JSONResponse({"detail": detail}, status_code=status)


class LocalGuard:
    def __init__(
        self,
        app: ASGIApp,
        *,
        hosts: Iterable[str],
        origins: Iterable[str],
        token: str,
    ) -> None:
        self.app = app
        self.hosts = frozenset(hosts)
        self.origins = frozenset(origins)
        self.token = token

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        response = None
        if headers.get("host", "") not in self.hosts:
            response = _reject(400, "Hôte non autorisé.")
        elif (origin := headers.get("origin")) is not None and origin not in self.origins:
            response = _reject(403, "Origine non autorisée.")
        elif scope["path"].startswith("/api") and not self._authorized(headers):
            response = _reject(401, "Jeton manquant ou invalide.")

        if response is not None:
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)

    def _authorized(self, headers: Headers) -> bool:
        scheme, _, credentials = headers.get("authorization", "").partition(" ")
        return scheme.lower() == "bearer" and secrets.compare_digest(credentials, self.token)
