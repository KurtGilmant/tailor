"""Extraction du texte d'un CV (PDF à couche texte ou DOCX). Pas d'OCR (hors périmètre)."""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import PurePath

import docx
import pdfplumber
from pdfminer.pdfdocument import PDFPasswordIncorrect
from pdfminer.pdfparser import PDFSyntaxError

MAX_BYTES = 10 * 1024 * 1024
# En dessous, on considère qu'il n'y a pas de vraie couche texte (scan, image).
MIN_TEXT_CHARS = 40


class CvTextError(Exception):
    """Message destiné à l'utilisateur, avec la marche à suivre."""


def extract_text(filename: str, data: bytes) -> str:
    if len(data) > MAX_BYTES:
        raise CvTextError("Fichier trop volumineux (10 Mo maximum).")
    suffix = PurePath(filename).suffix.lower()
    if suffix == ".pdf":
        text = _pdf_text(data)
    elif suffix == ".docx":
        text = _docx_text(data)
    else:
        raise CvTextError("Format non pris en charge : importe un PDF ou un DOCX.")
    return _tidy(text)


def _pdf_text(data: bytes) -> str:
    if not data.startswith(b"%PDF"):
        raise CvTextError("Ce fichier n'est pas un PDF valide.")
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            text = "\n\n".join(page.extract_text() or "" for page in pdf.pages)
    except PDFPasswordIncorrect:
        raise CvTextError("Ce PDF est protégé par un mot de passe.") from None
    except (PDFSyntaxError, ValueError):
        raise CvTextError("Ce PDF est illisible ou corrompu.") from None
    if len(text.strip()) < MIN_TEXT_CHARS:
        raise CvTextError(
            "Ce PDF ne contient pas de texte extractible (c'est probablement un scan). "
            "Importe plutôt la version DOCX de ton CV, ou saisis ton profil manuellement."
        )
    return text


def _docx_text(data: bytes) -> str:
    try:
        document = docx.Document(io.BytesIO(data))
    except (zipfile.BadZipFile, KeyError, ValueError):
        raise CvTextError("Ce fichier n'est pas un DOCX valide.") from None
    blocks = [p.text for p in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                blocks.append(" | ".join(dict.fromkeys(cells)))  # cellules fusionnées dédoublonnées
    text = "\n".join(blocks)
    if len(text.strip()) < MIN_TEXT_CHARS:
        raise CvTextError("Ce DOCX ne contient quasiment pas de texte.")
    return text


def _tidy(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    return re.sub(r"\n{3,}", "\n\n", text).strip()
