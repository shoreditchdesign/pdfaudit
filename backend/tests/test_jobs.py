from app.models.domain import CheckStatus, RuleResult
from app.services.jobs import JobManager
from app.services.rule_catalog import PDF_UA_RULE_IDS, RULE_DEFINITIONS


def _rule_result(rule_id: str, status: CheckStatus) -> RuleResult:
    definition = RULE_DEFINITIONS[rule_id]
    return RuleResult(
        rule_id=rule_id,
        theme=definition.theme,
        execution_mode=definition.execution_mode,
        status=status,
        evidence=[],
        remediation=definition.remediation_template,
        confidence=1.0,
        source="test",
    )


def test_pdf_ua_rollup_excludes_form_tooltip_rule() -> None:
    rule_results = {
        rule_id: _rule_result(rule_id, CheckStatus.PASS)
        for rule_id in RULE_DEFINITIONS
    }
    rule_results["form_fields_have_tu"] = _rule_result("form_fields_have_tu", CheckStatus.FAIL)

    result = JobManager._derive_bucket_result(PDF_UA_RULE_IDS, rule_results)

    assert result == CheckStatus.PASS


def test_wcag_rollup_ignores_adobe_manual_review_only_findings() -> None:
    rule_results = {
        rule_id: _rule_result(rule_id, CheckStatus.PASS)
        for rule_id in RULE_DEFINITIONS
    }
    rule_results["colour_contrast_machine_check"] = _rule_result(
        "colour_contrast_machine_check", CheckStatus.NEEDS_MANUAL_REVIEW
    )
    rule_results["reading_order_machine_check"] = _rule_result(
        "reading_order_machine_check", CheckStatus.NEEDS_MANUAL_REVIEW
    )
    rule_results["adobe_full_check"] = _rule_result("adobe_full_check", CheckStatus.NEEDS_MANUAL_REVIEW)

    result = JobManager._derive_wcag_bucket_result(rule_results)

    assert result == CheckStatus.NEEDS_MANUAL_REVIEW


def test_wcag_rollup_marks_api_unavailable_when_adobe_is_missing() -> None:
    rule_results = {
        rule_id: _rule_result(rule_id, CheckStatus.PASS)
        for rule_id in RULE_DEFINITIONS
    }
    rule_results["colour_contrast_machine_check"] = _rule_result(
        "colour_contrast_machine_check", CheckStatus.API_UNAVAILABLE
    )
    rule_results["reading_order_machine_check"] = _rule_result(
        "reading_order_machine_check", CheckStatus.API_UNAVAILABLE
    )
    rule_results["adobe_full_check"] = _rule_result("adobe_full_check", CheckStatus.API_UNAVAILABLE)

    result = JobManager._derive_wcag_bucket_result(rule_results)

    assert result == CheckStatus.API_UNAVAILABLE


def test_wcag_rollup_keeps_explicit_failures() -> None:
    rule_results = {
        rule_id: _rule_result(rule_id, CheckStatus.PASS)
        for rule_id in RULE_DEFINITIONS
    }
    rule_results["colour_contrast_machine_check"] = _rule_result("colour_contrast_machine_check", CheckStatus.FAIL)

    result = JobManager._derive_wcag_bucket_result(rule_results)

    assert result == CheckStatus.FAIL


def test_wcag_rollup_does_not_fail_on_adobe_full_check_alone() -> None:
    rule_results = {
        rule_id: _rule_result(rule_id, CheckStatus.PASS)
        for rule_id in RULE_DEFINITIONS
    }
    rule_results["adobe_full_check"] = _rule_result("adobe_full_check", CheckStatus.FAIL)

    result = JobManager._derive_wcag_bucket_result(rule_results)

    assert result == CheckStatus.PASS


def test_overall_result_follows_grouped_buckets_not_extra_subchecks() -> None:
    grouped_results = type(
        "GroupedResultsStub",
        (),
        {
            "pdf_ua_result": CheckStatus.PASS,
            "wcag_result": CheckStatus.NEEDS_MANUAL_REVIEW,
            "hsbc_policy_result": CheckStatus.PASS,
        },
    )()

    result = JobManager._derive_overall_result(grouped_results)

    assert result == CheckStatus.NEEDS_MANUAL_REVIEW
