from __future__ import annotations

from pathlib import Path

from app.services.checks.check_base import fail_result, manual_result, pass_result
from app.services.checks.pdf_check_utils import find_tags, get_outline_count, get_structure_elements, load_reader


def run(pdf_path: Path):
    try:
        reader = load_reader(pdf_path)
        page_count = len(reader.pages)
        elements = get_structure_elements(reader)
        toc_tags = find_tags(elements, "/TOC", "/TOCI")
        outline_count = get_outline_count(reader)

        if page_count < 5:
            return pass_result(f"TOC not required for {page_count}-page document.")
        if toc_tags or outline_count:
            return pass_result(
                f"Found TOC-related navigation ({len(toc_tags)} TOC tags, {outline_count} bookmarks)."
            )
        return fail_result(f"No TOC-related navigation found for {page_count}-page document.")
    except Exception as exc:
        return manual_result("TOC requirements could not be validated automatically.", notes=[str(exc)])
