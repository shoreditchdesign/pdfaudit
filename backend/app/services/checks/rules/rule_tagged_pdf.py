from __future__ import annotations

from pathlib import Path

from app.services.checks.check_base import fail_result, manual_result, pass_result
from app.services.checks.pdf_check_utils import has_tagged_pdf_structure, load_reader


def run(pdf_path: Path):
    try:
        reader = load_reader(pdf_path)
        has_tags, detail = has_tagged_pdf_structure(reader)
        if not has_tags:
            return fail_result(detail)
        return pass_result(detail)
    except Exception as exc:
        return manual_result("Tagged PDF status could not be validated automatically.", notes=[str(exc)])
