from __future__ import annotations

from pathlib import Path

from app.services.checks.base import fail_result, manual_result, pass_result
from app.services.checks.pdf_utils import is_probably_scanned, load_reader


def run(pdf_path: Path):
    try:
        reader = load_reader(pdf_path)
        scanned, message = is_probably_scanned(reader)
        if scanned:
            return fail_result(message)
        return pass_result(message)
    except Exception as exc:
        return manual_result("Extractable text could not be validated automatically.", notes=[str(exc)])
