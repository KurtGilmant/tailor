from pathlib import Path

import pytest
from pydantic import BaseModel, Field

from tailor.llm.errors import PromptError
from tailor.llm.prompts import PromptLibrary, parse_prompt
from tailor.llm.schema import strict_schema

from .conftest import DEMO_PROMPT


def test_render_fills_variables(prompts: PromptLibrary) -> None:
    rendered = prompts.get("demo").render({"text": "Jean, 32 ans"})
    assert rendered.user == "Texte : <<<Jean, 32 ans>>>"
    assert rendered.system.startswith("Tu extrais")
    assert rendered.version.startswith("1-")


def test_render_rejects_missing_and_unexpected_variables(prompts: PromptLibrary) -> None:
    with pytest.raises(PromptError, match="manquantes"):
        prompts.get("demo").render({})
    with pytest.raises(PromptError, match="inattendues"):
        prompts.get("demo").render({"text": "a", "typo": "b"})


def test_modified_prompt_changes_version(prompts: PromptLibrary, tmp_path: Path) -> None:
    before = prompts.get("demo").version
    path = tmp_path / "prompts" / "demo.md"
    path.write_text(DEMO_PROMPT.replace("Tu extrais", "Tu relèves"), encoding="utf-8")
    after = prompts.get("demo").version
    # Version déclarée inchangée (1) mais l'empreinte du contenu, elle, change.
    assert before.split("-")[0] == after.split("-")[0] == "1"
    assert before != after


def test_values_are_not_reinterpreted_as_placeholders(prompts: PromptLibrary) -> None:
    rendered = prompts.get("demo").render({"text": "{{text}} et {braces}"})
    assert rendered.user == "Texte : <<<{{text}} et {braces}>>>"


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ("pas de front-matter", "front-matter"),
        ("---\nversion: 1\n# system\nx", "non refermé"),
        ("---\nversion: un\n---\n# system\nx\n# user\ny", "version"),
        ("---\nversion: 1\n---\n# system\nx", "sections"),
    ],
)
def test_malformed_prompts(raw: str, message: str) -> None:
    with pytest.raises(PromptError, match=message):
        parse_prompt("x", raw)


def test_invalid_prompt_id_rejected(prompts: PromptLibrary) -> None:
    with pytest.raises(PromptError, match="invalide"):
        prompts.get("../secret")


class Skill(BaseModel):
    label: str
    default: bool = False  # une propriété nommée « default » doit survivre


class Profile(BaseModel):
    name: str
    nickname: str | None = None
    skills: list[Skill] = Field(default_factory=list)


def test_strict_schema_closes_objects_and_requires_everything() -> None:
    schema = strict_schema(Profile)
    assert schema["additionalProperties"] is False
    assert schema["required"] == ["name", "nickname", "skills"]
    skill = schema["$defs"]["Skill"]
    assert skill["additionalProperties"] is False
    assert skill["required"] == ["label", "default"]
    assert "default" in skill["properties"]
    assert "default" not in skill["properties"]["default"]  # mot-clé retiré, propriété gardée
