from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path

from openpyxl import Workbook, load_workbook

from app.models.domain import CheckStatus, DocumentAuditRecord, RetrievalCategory, SummaryMetrics
from app.services.rule_catalog import RULE_DEFINITIONS


RULE_COLUMNS = [
    "url_resolves",
    "url_is_expected_file",
    "unexpected_landing_page",
    "doc_title_present",
    "doc_language_present",
    "at_access_not_blocked",
    "extractable_text_present",
    "at_least_one_heading",
    "figure_alt_present",
    "bookmarks_present_if_gt_3_pages",
    "toc_present_general_doc_if_ge_5",
    "lists_use_l",
    "tables_use_table_tag",
    "links_use_link_tag",
    "form_fields_have_tu",
    "footnotes_use_note",
    "colour_contrast_machine_check",
    "reading_order_machine_check",
    "adobe_full_check",
]

REPORT_COLUMNS = [
    "ID",
    "Source Row Number",
    "PDF Name",
    "Original URL",
    "Final URL",
    "Run Timestamp",
    "Retrieval Category",
    "HTTP Status",
    "Redirect Count",
    "Content Type",
    "Page Title",
    "Page Count",
    "Overall Result",
    "PDF/UA Result",
    "WCAG Result",
    "HSBC Policy Result",
    *[RULE_DEFINITIONS[rule_id].title for rule_id in RULE_COLUMNS],
    "Failure Summary",
    "Failure Detail",
    "Remediation Guidance",
    "Manual Review Summary",
    "Notes",
]


class WorkbookTemplateResolver:
    def __init__(self, template_path: Path | None) -> None:
        self.template_path = template_path

    def create_workbook(self) -> Workbook:
        if self.template_path and self.template_path.exists():
            workbook = load_workbook(self.template_path)
            while len(workbook.worksheets) > 1:
                workbook.remove(workbook.worksheets[-1])
            sheet = workbook.worksheets[0]
            sheet.title = "Sheet1"
            if sheet.max_row > 0:
                sheet.delete_rows(1, sheet.max_row)
            return workbook

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Sheet1"
        return workbook


class ReportBuilder:
    def __init__(self, template_resolver: WorkbookTemplateResolver) -> None:
        self.template_resolver = template_resolver

    def build(self, rows: list[DocumentAuditRecord], summary: SummaryMetrics) -> bytes:
        workbook = self.template_resolver.create_workbook()
        sheet = workbook["Sheet1"]

        if sheet.max_row > 0:
            sheet.delete_rows(1, sheet.max_row)
        sheet.append(REPORT_COLUMNS)

        for row in rows:
            sheet.append(
                [
                    row.id,
                    row.source_row_number,
                    row.pdf_name,
                    row.original_url,
                    row.final_url,
                    summary.run_timestamp.isoformat(),
                    row.retrieval_category.value,
                    row.http_status,
                    row.redirect_count,
                    row.content_type,
                    row.page_title,
                    row.page_count,
                    row.overall_result.value,
                    row.grouped_results.pdf_ua_result.value,
                    row.grouped_results.wcag_result.value,
                    row.grouped_results.hsbc_policy_result.value,
                    *[row.rule_results[rule_id].status.value for rule_id in RULE_COLUMNS],
                    row.failure_summary,
                    row.failure_detail,
                    row.remediation_guidance,
                    row.manual_review_summary,
                    row.notes,
                ]
            )

        output = BytesIO()
        workbook.save(output)
        output.seek(0)
        return output.read()


def compute_summary(rows: list[DocumentAuditRecord]) -> SummaryMetrics:
    summary = SummaryMetrics(run_timestamp=datetime.utcnow())
    summary.total = len(rows)
    for row in rows:
        if row.retrieval_category != RetrievalCategory.DIRECT_FILE_OK:
            summary.unreachable_count += 1

        if row.overall_result == CheckStatus.PASS:
            summary.pass_count += 1
        elif row.overall_result == CheckStatus.FAIL:
            summary.fail_count += 1
        elif row.overall_result == CheckStatus.NEEDS_MANUAL_REVIEW:
            summary.manual_review_count += 1

        for rule_id, result in row.rule_results.items():
            if result.status == CheckStatus.FAIL:
                summary.per_rule_failures[rule_id] = summary.per_rule_failures.get(rule_id, 0) + 1

    return summary
