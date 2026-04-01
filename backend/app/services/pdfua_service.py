from __future__ import annotations

from pathlib import Path

from app.models.domain import CheckResult, CheckStatus, ExecutionMode, RuleResult
from app.services.checks.rules import (
    rule_alt_text,
    rule_bookmarks,
    rule_footnotes,
    rule_forms,
    rule_headings,
    rule_language,
    rule_links,
    rule_lists,
    rule_metadata,
    rule_scanned_pdf,
    rule_security,
    rule_tagged_pdf,
    rule_tables,
    rule_toc,
)
from app.services.audit_rule_catalog import RULE_DEFINITIONS


class Layer1Orchestrator:
    def run(self, pdf_path: Path) -> dict[str, RuleResult]:
        raw_results = {
            "doc_title_present": rule_metadata.run(pdf_path),
            "doc_language_present": rule_language.run(pdf_path),
            "at_access_not_blocked": rule_security.run(pdf_path),
            "extractable_text_present": rule_scanned_pdf.run(pdf_path),
            "tagged_pdf_present": rule_tagged_pdf.run(pdf_path),
            "at_least_one_heading": rule_headings.run(pdf_path),
            "figure_alt_present": rule_alt_text.run(pdf_path),
            "bookmarks_present_if_gt_3_pages": rule_bookmarks.run(pdf_path),
            "toc_present_general_doc_if_ge_5": rule_toc.run(pdf_path),
            "lists_use_l": rule_lists.run(pdf_path),
            "tables_use_table_tag": rule_tables.run(pdf_path),
            "links_use_link_tag": rule_links.run(pdf_path),
            "form_fields_have_tu": rule_forms.run(pdf_path),
            "footnotes_use_note": rule_footnotes.run(pdf_path),
        }
        return {rule_id: self._to_rule_result(rule_id, result) for rule_id, result in raw_results.items()}

    @staticmethod
    def _to_rule_result(rule_id: str, result: CheckResult) -> RuleResult:
        definition = RULE_DEFINITIONS[rule_id]
        status = result.status
        manual_review_reason = result.skipped_reason
        if status == CheckStatus.FAIL and definition.execution_mode != ExecutionMode.PYTHON_DETERMINISTIC:
            status = CheckStatus.NEEDS_MANUAL_REVIEW
            manual_review_reason = manual_review_reason or "This finding is not fully machine-verifiable and needs human review."
        return RuleResult(
            rule_id=rule_id,
            theme=definition.theme,
            execution_mode=definition.execution_mode,
            status=status,
            evidence=result.details,
            remediation=definition.remediation_template,
            confidence=1.0 if definition.execution_mode == ExecutionMode.PYTHON_DETERMINISTIC else 0.65,
            manual_review_reason=manual_review_reason,
            source="python",
            raw=result.raw,
        )
