from __future__ import annotations

from pathlib import Path

from app.services.checks.base import fail_result, manual_result, pass_result
from app.services.checks.pdf_utils import find_tags, get_structure_elements, load_reader


BANNED_PREFIXES = ("image of", "picture of", "graphic of")


def run(pdf_path: Path):
    try:
        reader = load_reader(pdf_path)
        elements = get_structure_elements(reader)
        figures = find_tags(elements, "/Figure")
        if not figures:
            return pass_result("No figure tags found in structure tree.")

        missing_alt: list[str] = []
        for index, figure in enumerate(figures, start=1):
            alt_text = (figure.alt_text or figure.actual_text or "").strip()
            if not alt_text:
                missing_alt.append(f"Figure {index} is missing /Alt text.")
                continue
            if len(alt_text) > 180:
                missing_alt.append(f"Figure {index} alt text exceeds 180 characters.")
                continue
            if alt_text.lower().startswith(BANNED_PREFIXES):
                missing_alt.append(f"Figure {index} alt text starts with a banned prefix: {alt_text}.")

        if missing_alt:
            return fail_result(*missing_alt)
        return pass_result(f"Validated alt text presence on {len(figures)} figure tags.")
    except Exception as exc:
        return manual_result("Figure alt text could not be validated automatically.", notes=[str(exc)])
