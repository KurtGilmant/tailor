"""Point d'entrée : création de l'application FastAPI et commande `tailor`."""

from __future__ import annotations

import argparse
import os
import threading
import webbrowser
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from tailor import __version__, db
from tailor.api import api_router, install_error_handlers
from tailor.config import Settings, load_settings
from tailor.llm import LLMConfig, LLMGateway
from tailor.llm.prompts import PromptLibrary
from tailor.security import LocalGuard, allowed_hosts, allowed_origins, dev_token, new_token

STATIC_DIR = Path(__file__).resolve().parent / "static"
TOKEN_ENV = "TAILOR_LAUNCH_TOKEN"  # noqa: S105 (nom de variable, pas un secret)


def create_app(
    settings: Settings,
    token: str,
    *,
    static_dir: Path = STATIC_DIR,
    prompts: PromptLibrary | None = None,
) -> FastAPI:
    # Validée dès la création : une configuration [llm] incohérente empêche le démarrage.
    llm_config = LLMConfig.from_raw(settings.llm)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        db.upgrade(settings.db_url)
        app.state.engine = db.make_engine(settings.db_url)
        app.state.llm = LLMGateway.from_config(app.state.engine, llm_config, prompts)
        yield
        app.state.engine.dispose()

    app = FastAPI(
        title="Tailor",
        version=__version__,
        lifespan=lifespan,
        # Pas de documentation exposée : le schéma est exporté par `python -m tailor.openapi`.
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.settings = settings
    app.include_router(api_router)
    install_error_handlers(app)
    _mount_frontend(app, static_dir)
    app.add_middleware(
        LocalGuard,
        hosts=allowed_hosts(settings.server.port),
        origins=allowed_origins(settings.server.port, dev=settings.dev),
        token=token,
    )
    return app


def _mount_frontend(app: FastAPI, static_dir: Path) -> None:
    """Sert le front buildé (SPA) : fichier existant sinon index.html."""
    if not (static_dir / "index.html").exists():
        return
    if (static_dir / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")
    root = static_dir.resolve()

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        if path.startswith("api/"):
            raise HTTPException(status_code=404)
        candidate = (root / path).resolve()
        if path and candidate.is_file() and candidate.is_relative_to(root):
            return FileResponse(candidate)
        return FileResponse(root / "index.html")


def app_factory() -> FastAPI:
    """Fabrique utilisée par uvicorn (y compris dans le processus de rechargement)."""
    return create_app(load_settings(), os.environ[TOKEN_ENV])


def main() -> None:
    parser = argparse.ArgumentParser(prog="tailor", description="Lance Tailor en local.")
    parser.add_argument("--reload", action="store_true", help="recharge à chaque modification")
    parser.add_argument("--no-browser", action="store_true", help="n'ouvre pas le navigateur")
    args = parser.parse_args()

    settings = load_settings()
    token = dev_token(settings.home) if settings.dev else new_token()
    os.environ[TOKEN_ENV] = token

    port = settings.server.port
    front = "http://localhost:5173" if settings.dev else f"http://127.0.0.1:{port}"
    url = f"{front}/?token={token}"
    print(f"\n  Tailor {__version__} — données : {settings.home}\n  Ouvrir : {url}\n", flush=True)
    if not settings.dev and not args.no_browser:
        threading.Timer(1.5, webbrowser.open, args=[url]).start()

    uvicorn.run(
        "tailor.main:app_factory",
        factory=True,
        host=settings.server.host,
        port=settings.server.port,
        reload=args.reload,
        reload_dirs=[str(Path(__file__).resolve().parent)] if args.reload else None,
        log_level="info",
    )
