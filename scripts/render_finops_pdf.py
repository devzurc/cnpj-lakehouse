"""Render the canonical Portuguese FinOps Markdown document to an A4 PDF."""

from __future__ import annotations

from pathlib import Path

import markdown
from weasyprint import HTML

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "finops-bigquery-architecture.md"
DESTINATION = SOURCE.with_suffix(".pdf")

CSS = """
@page {
  size: A4;
  margin: 14mm 15mm 15mm;
  @bottom-center { content: "CNPJ Lakehouse · " counter(page) " / " counter(pages); font-size: 7pt; color: #667085; }
}
html { font-family: "DejaVu Sans", sans-serif; color: #182230; font-size: 8.6pt; line-height: 1.35; }
body { margin: 0; }
h1 { color: #163a5f; font-size: 20pt; line-height: 1.1; margin: 0 0 8mm; }
h2 { color: #175cd3; font-size: 14pt; margin: 0 0 4mm; padding-bottom: 1.5mm; border-bottom: 0.4pt solid #b2ccff; page-break-before: always; }
h1 + h2 { page-break-before: avoid; }
h3 { color: #344054; font-size: 10.5pt; margin: 4mm 0 2mm; }
p { margin: 0 0 2.7mm; text-align: justify; }
ul, ol { margin: 1mm 0 3mm 5mm; padding-left: 4mm; }
li { margin-bottom: 1.3mm; }
pre { background: #f2f4f7; border-left: 2mm solid #84adff; padding: 3mm; font-size: 7.2pt; line-height: 1.25; white-space: pre-wrap; }
code { font-family: "DejaVu Sans Mono", monospace; font-size: 0.9em; }
table { border-collapse: collapse; width: 100%; margin: 2mm 0 4mm; font-size: 7.5pt; }
th { background: #eaf2ff; color: #163a5f; }
th, td { border: 0.35pt solid #98a2b3; padding: 1.4mm; vertical-align: top; }
a { color: #175cd3; text-decoration: none; }
strong { color: #101828; }
"""


def main() -> None:
    html_body = markdown.markdown(
        SOURCE.read_text(encoding="utf-8"),
        extensions=("fenced_code", "tables", "sane_lists"),
    )
    document = f"<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'><style>{CSS}</style></head><body>{html_body}</body></html>"
    HTML(string=document, base_url=str(ROOT)).write_pdf(DESTINATION)
    print(f"PDF rendered: {DESTINATION}")


if __name__ == "__main__":
    main()
