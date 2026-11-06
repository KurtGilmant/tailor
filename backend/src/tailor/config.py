"""Configuration de l'application et dossier de données local.

Les données vivent hors du dépôt, dans le dossier applicatif de l'OS
(`~/Library/Application Support/Tailor` sur macOS), surchargeable par `TAILOR_HOME`.
La configuration utilisateur est lue depuis `<home>/tailor.toml` si le fichier existe.
"""

from __future__ import annotations

import os
import stat
import tomllib
from functools import cached_property
from pathlib import Path

from platformdirs import user_data_dir
from pydantic import BaseModel, Field

APP_NAME = "Tailor"
HOME_DIR_MODE = 0o700


class ServerSettings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8765


class Settings(BaseModel):
    home: Path
    dev: bool = False
    server: ServerSettings = Field(default_factory=ServerSettings)
    # Section [llm] du fichier tailor.toml, interprétée par tailor.llm.config.
    llm: dict = Field(default_factory=dict)

    @cached_property
    def db_path(self) -> Path:
        return self.home / "tailor.db"

    @property
    def db_url(self) -> str:
        return f"sqlite:///{self.db_path}"

    @property
    def files_dir(self) -> Path:
        return self.home / "files"

    @property
    def config_file(self) -> Path:
        return self.home / "tailor.toml"


def default_home() -> Path:
    override = os.environ.get("TAILOR_HOME")
    if override:
        return Path(override).expanduser()
    return Path(user_data_dir(APP_NAME, appauthor=False))


def ensure_home(home: Path) -> Path:
    """Crée le dossier de données et force des permissions propriétaire uniquement."""
    home.mkdir(parents=True, exist_ok=True)
    if stat.S_IMODE(home.stat().st_mode) != HOME_DIR_MODE:
        home.chmod(HOME_DIR_MODE)
    (home / "files").mkdir(mode=HOME_DIR_MODE, exist_ok=True)
    return home


def load_settings(home: Path | None = None) -> Settings:
    home = ensure_home(home or default_home())
    data: dict = {}
    config_file = home / "tailor.toml"
    if config_file.exists():
        data = tomllib.loads(config_file.read_text(encoding="utf-8"))
    return Settings(
        home=home,
        dev=os.environ.get("TAILOR_DEV") == "1",
        server=ServerSettings(**data.get("server", {})),
        llm=data.get("llm", {}),
    )
