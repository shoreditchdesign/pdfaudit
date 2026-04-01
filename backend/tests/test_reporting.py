from io import BytesIO

from openpyxl import load_workbook

from app.models.domain import (
    CheckStatus,
    DocumentAuditRecord,
    GroupedResults,
    RetrievalCategory,
    RuleResult,
)
from app.services.reporting import REPORT_COLUMNS, ReportBuilder, WorkbookTemplateResolver, compute_summary
from app.services.rule_catalog import RULE_DEFINITIONS


def _rule_result(rule_id: str, status: CheckStatus) -> RuleResult:
    definition = RULE_DEFINITIONS[rule_id]
    return RuleResult(
        rule_id=rule_id,
        theme=definition.theme,
        execution_mode=definition.execution_mode,
        status=status,
        evidence=["test evidence"] if status != CheckStatus.PASS else [],
        remediation=definition.remediation_template,
        confidence=1.0,
        source="test",
    )


def _record(status: CheckStatus) -> DocumentAuditRecord:
    results = {
        rule_id: _rule_result(rule_id, CheckStatus.PASS)
        for rule_id in RULE_DEFINITIONS
    }
    results["doc_title_present"] = _rule_result("doc_title_present", status)
    return DocumentAuditRecord(
        id=1,
        original_url="https://example.com/test.pdf",
        final_url="https://example.com/test.pdf",
        http_status="200",
        retrieval_category=RetrievalCategory.DIRECT_FILE_OK,
        overall_result=status,
        grouped_results=GroupedResults(
            pdf_ua_result=status,
            wcag_result=status,
            hsbc_policy_result=CheckStatus.PASS,
        ),
        rule_results=results,
        failure_summary="Document Title" if status != CheckStatus.PASS else "",
        failure_detail="Document Title: missing title metadata" if status != CheckStatus.PASS else "",
        remediation_guidance="Set document title metadata." if status != CheckStatus.PASS else "",
        manual_review_summary="",
        notes="",
    )


def test_compute_summary_counts_rule_failures() -> None:
    rows = [_record(CheckStatus.FAIL)]
    summary = compute_summary(rows)
    assert summary.total == 1
    assert summary.fail_count == 1
    assert summary.per_rule_failures["doc_title_present"] == 1


def test_report_builder_returns_workbook_bytes() -> None:
    rows = [_record(CheckStatus.PASS)]
    summary = compute_summary(rows)
    builder = ReportBuilder(WorkbookTemplateResolver(template_path=None))
    report = builder.build(rows, summary)
    assert report[:2] == b"PK"

    workbook = load_workbook(BytesIO(report))
    sheet = workbook["Sheet1"]
    assert workbook.sheetnames == ["Sheet1"]
    assert sheet.max_row == 2
    assert sheet["A1"].value == "PDF Name"
    assert sheet["B2"].value == "Open PDF"
    assert sheet["B2"].hyperlink.target == "https://example.com/test.pdf"
    assert sheet["F2"].value == "Complete"
    assert sheet["H2"].value == "Pass"
    assert sheet["I2"].value == "Pass"
    assert REPORT_COLUMNS[19] == "Original URL"
