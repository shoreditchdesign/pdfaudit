from __future__ import annotations

from pathlib import Path

from app.services.checks.base import fail_result, manual_result, pass_result
from app.services.checks.pdf_utils import display_doc_title_enabled, get_metadata_title, load_reader


def run(pdf_path: Path):
    try:
        reader = load_reader(pdf_path)
        title = get_metadata_title(reader)
        if not title:
            return fail_result("Document title metadata is missing.")

        if not display_doc_title_enabled(reader):
            return fail_result(
                f"Document title metadata is present ({title}) but DisplayDocTitle is not enabled."
            )

        return pass_result(f"Document title metadata present: {title}")
    except Exception as exc:
        return manual_result("Metadata could not be validated automatically.", notes=[str(exc)])
