from __future__ import annotations

from pathlib import Path

from app.services.checks.check_base import fail_result, manual_result, pass_result
from app.services.checks.pdf_check_utils import find_tags, get_structure_elements, load_reader


def run(pdf_path: Path):
    try:
        reader = load_reader(pdf_path)
        elements = get_structure_elements(reader)
        list_tags = find_tags(elements, "/L")
        item_tags = find_tags(elements, "/LI")
        label_tags = find_tags(elements, "/Lbl")
        body_tags = find_tags(elements, "/LBody")

        if not list_tags and not item_tags:
            return pass_result("No list tags found in structure tree.")
        if item_tags and not list_tags:
            return fail_result("List item tags found without a parent /L list tag.")
        if item_tags and (not label_tags or not body_tags):
            return fail_result("List items are missing /Lbl or /LBody tags.")
        return pass_result(
            f"Found {len(list_tags)} list tags and {len(item_tags)} list item tags."
        )
    except Exception as exc:
        return manual_result("List structure could not be validated automatically.", notes=[str(exc)])
