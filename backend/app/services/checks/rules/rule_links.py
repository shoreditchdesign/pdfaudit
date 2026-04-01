from __future__ import annotations

from pathlib import Path

from app.services.checks.check_base import fail_result, manual_result, pass_result
from app.services.checks.pdf_check_utils import count_link_annotations, find_tags, get_structure_elements, load_reader


def run(pdf_path: Path):
    try:
        reader = load_reader(pdf_path)
        link_annotations = count_link_annotations(reader)
        link_tags = find_tags(get_structure_elements(reader), "/Link")

        if link_annotations == 0 and not link_tags:
            return pass_result("No links found in annotations or structure tree.")
        if link_annotations > 0 and not link_tags:
            return fail_result(
                f"Found {link_annotations} link annotations but no /Link tags in the structure tree."
            )
        return pass_result(
            f"Found {len(link_tags)} /Link tags for {link_annotations} link annotations."
        )
    except Exception as exc:
        return manual_result("Link tagging could not be validated automatically.", notes=[str(exc)])
