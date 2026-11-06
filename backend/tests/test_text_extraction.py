import pytest

from tailor.profile.text_extraction import CvTextError, extract_text

from .cv_fixtures import cv_docx, cv_pdf, scanned_pdf


def test_pdf_with_text_layer() -> None:
    text = extract_text("cv.pdf", cv_pdf())
    assert "Léa Martin" in text
    assert "Réduction de 20 % du temps de traitement" in text
    assert "Université de Bordeaux" in text


def test_scanned_pdf_refused_with_guidance() -> None:
    with pytest.raises(CvTextError, match="scan") as error:
        extract_text("cv.pdf", scanned_pdf())
    assert "DOCX" in str(error.value) and "manuellement" in str(error.value)


def test_docx_paragraphs_and_tables() -> None:
    text = extract_text("CV.DOCX", cv_docx())
    assert "Société Exemple" in text
    assert "Réduction de 20 % du temps de traitement" in text
    assert "Langues | Anglais C1" in text


@pytest.mark.parametrize(
    ("filename", "data", "message"),
    [
        ("cv.txt", b"bonjour", "Format non pris en charge"),
        ("cv.pdf", b"pas un pdf", "pas un PDF valide"),
        ("cv.docx", b"pas un zip", "pas un DOCX valide"),
        ("cv.pdf", b"%PDF" + b"0" * (10 * 1024 * 1024), "trop volumineux"),
    ],
)
def test_invalid_files(filename: str, data: bytes, message: str) -> None:
    with pytest.raises(CvTextError, match=message):
        extract_text(filename, data)
