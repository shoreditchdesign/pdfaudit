from __future__ import annotations

from pathlib import Path

from app.models.domain import CheckResult, ExecutionMode, RuleResult
from app.services.checks.rules import (
    alt_text,
    bookmarks,
    footnotes,
    forms,
    headings,
    language,
    links,
    lists,
    metadata,
    scanned_pdf,
    security,
    tables,
    toc,
)
from app.services.rule_catalog import RULE_DEFINITIONS


class Layer1Orchestrator:
    def run(self, pdf_path: Path) -> dict[str, RuleResult]:
        raw_results = {
            "doc_title_present": metadata.run(pdf_path),
            "doc_language_present": language.run(pdf_path),
            "at_access_not_blocked": security.run(pdf_path),
            "extractable_text_present": scanned_pdf.run(pdf_path),
            "at_least_one_heading": headings.run(pdf_path),
            "figure_alt_present": alt_text.run(pdf_path),
            "bookmarks_present_if_gt_3_pages": bookmarks.run(pdf_path),
            "toc_present_general_doc_if_ge_5": toc.run(pdf_path),
            "lists_use_l": lists.run(pdf_path),
            "tables_use_table_tag": tables.run(pdf_path),
            "links_use_link_tag": links.run(pdf_path),
            "form_fields_have_tu": forms.run(pdf_path),
            "footnotes_use_note": footnotes.run(pdf_path),
        }
        return {rule_id: self._to_rule_result(rule_id, result) for rule_id, result in raw_results.items()}

    @staticmethod
    def _to_rule_result(rule_id: str, result: CheckResult) -> RuleResult:
        definition = RULE_DEFINITIONS[rule_id]
        return RuleResult(
            rule_id=rule_id,
            theme=definition.theme,
            execution_mode=definition.execution_mode,
            status=result.status,
            evidence=result.details,
            remediation=definition.remediation_template,
            confidence=1.0 if definition.execution_mode == ExecutionMode.PYTHON_DETERMINISTIC else 0.65,
            manual_review_reason=result.skipped_reason,
            source="python",
            raw=result.raw,
        )
