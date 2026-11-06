"""Prompts versionnés, stockés comme fichiers texte dans `prompts/` à la racine du dépôt.

Format d'un fichier `prompts/<id>.md` :

    ---
    version: 1
    description: Extraction des exigences d'une offre
    ---
    # system
    Tu es ...
    # user
    Voici l'offre : {{offer_text}}

La version enregistrée avec chaque résultat est `<version déclarée>-<empreinte>` :
l'empreinte du contenu change à chaque modification, même si l'auteur oublie
d'incrémenter la version déclarée.
"""

from __future__ import annotations

import hashlib
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from tailor.llm.errors import PromptError

# backend/src/tailor/llm/prompts.py -> racine du dépôt
DEFAULT_PROMPTS_DIR = Path(__file__).resolve().parents[4] / "prompts"
_PROMPT_ID = re.compile(r"^[a-z0-9][a-z0-9_\-]*$")
_PLACEHOLDER = re.compile(r"\{\{\s*(\w+)\s*\}\}")
_SECTION = re.compile(r"^# (system|user)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class RenderedPrompt:
    prompt_id: str
    version: str
    system: str
    user: str


@dataclass(frozen=True)
class Prompt:
    id: str
    version: str
    system: str
    user: str

    @property
    def variables(self) -> frozenset[str]:
        return frozenset(_PLACEHOLDER.findall(self.system + self.user))

    def render(self, inputs: Mapping[str, str]) -> RenderedPrompt:
        missing = self.variables - inputs.keys()
        unexpected = inputs.keys() - self.variables
        if missing or unexpected:
            raise PromptError(
                f"Prompt « {self.id} » : variables manquantes {sorted(missing)}, "
                f"inattendues {sorted(unexpected)}."
            )

        def fill(template: str) -> str:
            return _PLACEHOLDER.sub(lambda m: str(inputs[m.group(1)]), template)

        return RenderedPrompt(self.id, self.version, fill(self.system), fill(self.user))


def parse_prompt(prompt_id: str, raw: str) -> Prompt:
    if not raw.startswith("---\n"):
        raise PromptError(f"Prompt « {prompt_id} » : front-matter `---` attendu en tête.")
    try:
        header, body = raw[4:].split("\n---\n", 1)
    except ValueError:
        raise PromptError(f"Prompt « {prompt_id} » : front-matter non refermé.") from None

    meta = dict(
        (key.strip(), value.strip())
        for key, _, value in (line.partition(":") for line in header.splitlines() if line.strip())
    )
    declared = meta.get("version", "")
    if not declared.isdigit():
        raise PromptError(f"Prompt « {prompt_id} » : `version` entière obligatoire.")

    parts = _SECTION.split(body)
    # parts = [préambule, "system", texte, "user", texte]
    sections = dict(zip(parts[1::2], (text.strip() for text in parts[2::2]), strict=True))
    if set(sections) != {"system", "user"}:
        raise PromptError(f"Prompt « {prompt_id} » : sections `# system` et `# user` requises.")

    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]
    return Prompt(prompt_id, f"{declared}-{digest}", sections["system"], sections["user"])


class PromptLibrary:
    def __init__(self, directory: Path | None = None) -> None:
        env = os.environ.get("TAILOR_PROMPTS_DIR")
        self.directory = directory or (Path(env) if env else DEFAULT_PROMPTS_DIR)

    def get(self, prompt_id: str) -> Prompt:
        if not _PROMPT_ID.match(prompt_id):
            raise PromptError(f"Identifiant de prompt invalide : « {prompt_id} ».")
        path = self.directory / f"{prompt_id}.md"
        if not path.is_file():
            raise PromptError(f"Prompt introuvable : {path}.")
        return parse_prompt(prompt_id, path.read_text(encoding="utf-8"))
