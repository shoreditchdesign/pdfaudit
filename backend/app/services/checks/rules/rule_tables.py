from __future__ import annotations

from pathlib import Path

from app.services.checks.check_base import fail_result, manual_result, pass_result
from app.services.checks.pdf_check_utils import find_tags, get_structure_elements, load_reader


def run(pdf_path: Path):
    try:
        reader = load_reader(pdf_path)
        elements = get_structure_elements(reader)
        table_tags = find_tags(elements, "/Table")
        row_tags = find_tags(elements, "/TR")
        header_tags = find_tags(elements, "/TH")
        data_tags = find_tags(elements, "/TD")

        if not table_tags and not row_tags and not header_tags and not data_tags:
            return pass_result("No table tags found in structure tree.")
        if table_tags and not row_tags:
            return fail_result("Table tags found without /TR row tags.")
        if row_tags and not (header_tags or data_tags):
            return fail_result("Table rows found without /TH or /TD cells.")
        return pass_result(
            f"Found {len(table_tags)} table tags, {len(row_tags)} rows, {len(header_tags)} headers, and {len(data_tags)} data cells."
        )
    except Exception as exc:
        return manual_result("Table structure could not be validated automatically.", notes=[str(exc)])
