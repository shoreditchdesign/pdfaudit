from __future__ import annotations

from pathlib import Path

from app.services.checks.check_base import fail_result, manual_result, pass_result
from app.services.checks.pdf_check_utils import find_tags, get_structure_elements, load_reader


def run(pdf_path: Path):
    try:
        reader = load_reader(pdf_path)
        elements = get_structure_elements(reader)
        note_tags = find_tags(elements, "/Note")
        label_tags = find_tags(elements, "/Lbl")

        if not note_tags:
            return pass_result("No footnote tags found in structure tree.")
        if note_tags and not label_tags:
            return fail_result("Footnote /Note tags found without /Lbl labels.")
        return pass_result(f"Found {len(note_tags)} footnote tags with labels present.")
    except Exception as exc:
        return manual_result("Footnotes could not be validated automatically.", notes=[str(exc)])
