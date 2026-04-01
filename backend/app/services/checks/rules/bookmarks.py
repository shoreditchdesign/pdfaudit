from __future__ import annotations

from pathlib import Path

from app.services.checks.base import fail_result, manual_result, pass_result
from app.services.checks.pdf_utils import get_outline_count, load_reader


def run(pdf_path: Path):
    try:
        reader = load_reader(pdf_path)
        page_count = len(reader.pages)
        outline_count = get_outline_count(reader)
        if page_count <= 3:
            return pass_result(f"Bookmarks optional for {page_count}-page document.")
        if outline_count == 0:
            return fail_result(f"No bookmarks found for {page_count}-page document.")
        return pass_result(f"Found {outline_count} bookmarks for {page_count}-page document.")
    except Exception as exc:
        return manual_result("Bookmarks could not be validated automatically.", notes=[str(exc)])
