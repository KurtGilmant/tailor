"""Exporte le schéma OpenAPI sur la sortie standard : `python -m tailor.openapi`.

Le front génère son client typé à partir de ce fichier (`make api-client`).
"""

import json
import sys
import tempfile
from pathlib import Path

from tailor.config import Settings
from tailor.main import create_app


def build_schema() -> dict:
    # Aucune base n'est ouverte : le lifespan ne s'exécute pas pour générer le schéma.
    settings = Settings(home=Path(tempfile.gettempdir()))
    return create_app(settings, token="schema-only").openapi()  # noqa: S106


if __name__ == "__main__":
    json.dump(build_schema(), sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
