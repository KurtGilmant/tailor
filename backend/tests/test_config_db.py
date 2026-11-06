import stat
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect

from tailor import db
from tailor.config import ensure_home, load_settings


def test_home_created_owner_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "fresh"
    monkeypatch.setenv("TAILOR_HOME", str(home))
    settings = load_settings()
    assert settings.home == home
    assert stat.S_IMODE(home.stat().st_mode) == 0o700
    assert (home / "files").is_dir()


def test_home_permissions_tightened(tmp_path: Path) -> None:
    home = tmp_path / "loose"
    home.mkdir(mode=0o755)
    home.chmod(0o755)
    ensure_home(home)
    assert stat.S_IMODE(home.stat().st_mode) == 0o700


def test_config_file_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "cfg"
    home.mkdir()
    (home / "tailor.toml").write_text('[server]\nport = 9999\n[llm]\nmode = "local"\n')
    monkeypatch.setenv("TAILOR_HOME", str(home))
    settings = load_settings()
    assert settings.server.port == 9999
    assert settings.llm == {"mode": "local"}


def test_migrations_upgrade_and_downgrade(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'm.db'}"
    db.upgrade(url)
    assert "alembic_version" in inspect(create_engine(url)).get_table_names()
    db.downgrade(url, "base")
    with create_engine(url).connect() as conn:
        rows = conn.exec_driver_sql("SELECT version_num FROM alembic_version").fetchall()
    assert rows == []


def test_example_config_is_valid() -> None:
    """La configuration d'exemple documentée doit rester acceptée par le code."""
    import tomllib

    from tailor.llm import LLMConfig, Task

    example = Path(__file__).resolve().parents[2] / "tailor.example.toml"
    raw = tomllib.loads(example.read_text(encoding="utf-8"))
    config = LLMConfig.from_raw(raw["llm"])
    assert config.routes[Task.EXTRACT].model == "claude-opus-5-5"
    assert config.providers["ollama"].is_cloud is False
