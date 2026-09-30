"""Validate the FinOps PDF page range and required Portuguese content."""

from __future__ import annotations

import argparse
from pathlib import Path

from pypdf import PdfReader

REQUIRED_TERMS = (
    "GCS Bronze",
    "BigQuery",
    "require_partition_filter",
    "MERGE",
    "bytes processados",
    "slot-ms",
    "onboarding",
    "Lakehouse CNPJ",
)

A4_WIDTH_POINTS = 595.28
A4_HEIGHT_POINTS = 841.89


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    args = parser.parse_args()
    reader = PdfReader(args.pdf)
    page_count = len(reader.pages)
    if not 4 <= page_count <= 7:
        raise SystemExit(f"expected 4–7 A4 pages; found {page_count}")
    for index, page in enumerate(reader.pages, start=1):
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        if abs(width - A4_WIDTH_POINTS) > 3 or abs(height - A4_HEIGHT_POINTS) > 3:
            raise SystemExit(f"page {index} is not A4: {width:.1f}×{height:.1f} points")
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    missing = [term for term in REQUIRED_TERMS if term.casefold() not in text.casefold()]
    if missing:
        raise SystemExit(f"FinOps PDF is missing required terms: {missing}")
    print(f"FinOps PDF verified: {page_count} pages, required content present")


if __name__ == "__main__":
    main()
