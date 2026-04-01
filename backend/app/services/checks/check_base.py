from __future__ import annotations

from app.models.domain import CheckResult, CheckStatus


def pass_result(*details: str) -> CheckResult:
    return CheckResult(status=CheckStatus.PASS, details=list(details))


def fail_result(*details: str, notes: list[str] | None = None) -> CheckResult:
    return CheckResult(status=CheckStatus.FAIL, details=list(details), notes=notes or [])


def manual_result(*details: str, notes: list[str] | None = None) -> CheckResult:
    return CheckResult(
        status=CheckStatus.NEEDS_MANUAL_REVIEW,
        details=list(details),
        notes=notes or [],
    )


def api_unavailable_result(*details: str) -> CheckResult:
    return CheckResult(status=CheckStatus.API_UNAVAILABLE, details=list(details))


def na_result(reason: str) -> CheckResult:
    return CheckResult(status=CheckStatus.NA, skipped_reason=reason)

