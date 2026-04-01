from __future__ import annotations

from pathlib import Path

from app.services.checks.check_base import fail_result, manual_result, pass_result
from app.services.checks.pdf_check_utils import get_language, load_reader


def run(pdf_path: Path):
    try:
        reader = load_reader(pdf_path)
        language = get_language(reader)
        if not language:
            return fail_result("PDF catalog is missing /Lang.")
        return pass_result(f"PDF catalog language is set to {language}.")
    except Exception as exc:
        return manual_result("Language could not be validated automatically.", notes=[str(exc)])
