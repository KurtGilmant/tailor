"""Point d'import unique des tables SQLModel (lu par Alembic pour l'autogénération).

Chaque module qui déclare des tables est importé ici.
"""

from tailor.llm import models as llm_models

__all__ = ["llm_models"]
