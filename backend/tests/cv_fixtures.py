"""CV fictifs générés à la volée (aucun binaire versionné, aucune donnée réelle)."""

import io

import docx
import typst

CV_TYPST = """#set page(width: 21cm, height: auto, margin: 1.5cm)
#set text(lang: "fr")
= Léa Martin
Ingénieure données · lea.martin\\@example.org · Bordeaux

== Expérience
*Ingénieure données* — Société Exemple (2023-09 – aujourd'hui)
- Réduction de 20 % du temps de traitement des flux de facturation
- Mise en place d'une chaîne d'intégration continue avec GitHub Actions

== Formation
Master Intelligence artificielle — Université de Bordeaux (2021 – 2023)

== Compétences
Python, SQL, Docker
"""


def cv_pdf() -> bytes:
    return typst.compile(CV_TYPST.encode("utf-8"), format="pdf")


def scanned_pdf() -> bytes:
    """Une page sans aucune couche texte, comme un CV scanné."""
    source = b"#set page(width: 21cm, height: 29.7cm)\n#rect(width: 15cm, height: 20cm, fill: gray)"
    return typst.compile(source, format="pdf")


def cv_docx() -> bytes:
    document = docx.Document()
    document.add_heading("Léa Martin", 0)
    document.add_paragraph("Ingénieure données · lea.martin@example.org · Bordeaux")
    document.add_heading("Expérience", 1)
    document.add_paragraph("Ingénieure données — Société Exemple (2023-09 – aujourd'hui)")
    document.add_paragraph("Réduction de 20 % du temps de traitement", style="List Bullet")
    table = document.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "Langues"
    table.rows[0].cells[1].text = "Anglais C1"
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()
