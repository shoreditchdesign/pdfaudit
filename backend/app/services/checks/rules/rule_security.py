from __future__ import annotations

from pathlib import Path

from app.services.checks.check_base import fail_result, manual_result, pass_result
from app.services.checks.pdf_check_utils import get_user_access_summary, load_reader


def run(pdf_path: Path):
    try:
        reader = load_reader(pdf_path)
        allowed, message = get_user_access_summary(reader)
        if allowed:
            return pass_result(message)
        return fail_result(message)
    except Exception as exc:
        return manual_result("Security permissions could not be validated automatically.", notes=[str(exc)])
