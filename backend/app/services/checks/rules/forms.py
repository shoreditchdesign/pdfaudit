from __future__ import annotations

from pathlib import Path

from app.services.checks.base import fail_result, pass_result, manual_result
from app.services.checks.pdf_utils import get_form_field_objects, get_form_tooltips, get_page_tab_order_issues, load_reader


def run(pdf_path: Path):
    try:
        reader = load_reader(pdf_path)
        fields = get_form_field_objects(reader)
        if not fields:
            return pass_result("No AcroForm fields found.")

        issues: list[str] = []
        tooltips = get_form_tooltips(reader)
        if len(tooltips) != len(fields):
            issues.append("One or more form fields are missing /TU tooltips.")

        duplicates = {tooltip for tooltip in tooltips if tooltips.count(tooltip) > 1}
        if duplicates:
            issues.append(f"Duplicate tooltip values found: {', '.join(sorted(duplicates))}.")

        for tooltip in tooltips:
            if len(tooltip) > 100:
                issues.append(f"Tooltip exceeds 100 characters: {tooltip}.")

        tab_order_issues = get_page_tab_order_issues(reader)
        if tab_order_issues:
            issues.append(
                f"Page tab order is not structure-based on pages: {', '.join(str(page) for page in tab_order_issues)}."
            )

        if issues:
            return fail_result(*issues)
        return pass_result(f"Validated tooltip coverage for {len(fields)} form fields.")
    except Exception as exc:
        return manual_result("Form accessibility checks could not be validated automatically.", notes=[str(exc)])
