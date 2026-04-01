from __future__ import annotations

from pathlib import Path

from app.services.checks.base import fail_result, manual_result, pass_result
from app.services.checks.pdf_utils import get_heading_levels, get_structure_elements, load_reader


def run(pdf_path: Path):
    try:
        reader = load_reader(pdf_path)
        levels = get_heading_levels(get_structure_elements(reader))
        if not levels:
            return fail_result("No heading tags found in structure tree.")

        issues: list[str] = []
        h1_count = sum(level == 1 for level in levels)
        if h1_count == 0:
            issues.append("No H1 heading found.")
        elif h1_count > 1:
            issues.append(f"Multiple H1 headings found ({h1_count}).")

        for previous, current in zip(levels, levels[1:]):
            if current > previous + 1:
                issues.append(f"Heading level skipped from H{previous} to H{current}.")

        if issues:
            return fail_result(*issues)
        return pass_result(f"Heading structure validated across {len(levels)} heading tags.")
    except Exception as exc:
        return manual_result("Heading structure could not be validated automatically.", notes=[str(exc)])
