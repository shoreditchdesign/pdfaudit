from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import requests

from app.core.config import Settings
from app.models.domain import CheckStatus, ExecutionMode, RuleResult
from app.services.checks.check_base import api_unavailable_result, fail_result, manual_result, pass_result
from app.services.audit_rule_catalog import RULE_DEFINITIONS


ADOBE_RULE_IDS = (
    "colour_contrast_machine_check",
    "reading_order_machine_check",
    "adobe_full_check",
)


class AdobeAPIError(RuntimeError):
    pass


@dataclass
class AdobeReportSummary:
    raw_report: dict[str, Any]
    overall_status: CheckStatus
    overall_evidence: list[str]
    colour_status: CheckStatus
    colour_evidence: list[str]
    reading_order_status: CheckStatus
    reading_order_evidence: list[str]


class AdobeClient:
    def __init__(self, settings: Settings, enabled: bool) -> None:
        self.settings = settings
        self.enabled = enabled
        self.base_url = settings.adobe_pdf_services_base_url
        self.poll_interval = settings.adobe_poll_interval_seconds
        self.poll_timeout = settings.adobe_poll_timeout_seconds
        self.session = requests.Session()

    def check_document(self, pdf_path: str) -> dict[str, RuleResult]:
        if not self.enabled:
            unavailable = api_unavailable_result("Adobe API unavailable or disabled for this run.")
            return {
                rule_id: self._to_rule_result(rule_id, unavailable, "adobe", None)
                for rule_id in ADOBE_RULE_IDS
            }

        if not self.settings.adobe_configured:
            unavailable = api_unavailable_result(
                "Adobe credentials are missing. Set ADOBE_CLIENT_ID and ADOBE_CLIENT_SECRET in the root .env file."
            )
            return {
                rule_id: self._to_rule_result(rule_id, unavailable, "adobe", None)
                for rule_id in ADOBE_RULE_IDS
            }

        try:
            report = self._run_accessibility_job(Path(pdf_path))
            return self._map_report_to_rule_results(report)
        except AdobeAPIError as exc:
            unavailable = api_unavailable_result(f"Adobe API request failed: {exc}")
            return {
                rule_id: self._to_rule_result(rule_id, unavailable, "adobe", {"error": str(exc)})
                for rule_id in ADOBE_RULE_IDS
            }
        except Exception as exc:
            manual = manual_result("Adobe report could not be parsed cleanly.", notes=[str(exc)])
            return {
                rule_id: self._to_rule_result(rule_id, manual, "adobe", {"error": str(exc)})
                for rule_id in ADOBE_RULE_IDS
            }

    def _run_accessibility_job(self, pdf_path: Path) -> dict[str, Any]:
        access_token = self._fetch_access_token()
        asset = self._create_asset(access_token)
        self._upload_asset(asset["uploadUri"], pdf_path)
        location = self._submit_job(access_token, asset["assetID"])
        result = self._poll_for_result(access_token, location)
        report_url = self._extract_report_download_url(result)
        report_response = self.session.get(report_url, timeout=60)
        report_response.raise_for_status()
        return report_response.json()

    def _fetch_access_token(self) -> str:
        response = self.session.post(
            "https://ims-na1.adobelogin.com/ims/token/v3",
            data={
                "grant_type": "client_credentials",
                "client_id": self.settings.adobe_client_id or "",
                "client_secret": self.settings.adobe_client_secret or "",
                **({"scope": self.settings.adobe_scope} if self.settings.adobe_scope else {}),
            },
            timeout=30,
        )
        if response.status_code >= 400:
            raise AdobeAPIError(f"Token request failed with {response.status_code}: {response.text[:200]}")
        token = response.json().get("access_token")
        if not token:
            raise AdobeAPIError("Token response did not include an access token.")
        return token

    def _headers(self, access_token: str) -> dict[str, str]:
        return {
            "x-api-key": self.settings.adobe_client_id or "",
            "Authorization": f"Bearer {access_token}",
        }

    def _create_asset(self, access_token: str) -> dict[str, Any]:
        response = self.session.post(
            f"{self.base_url}/assets",
            headers={**self._headers(access_token), "Content-Type": "application/json"},
            json={"mediaType": "application/pdf"},
            timeout=30,
        )
        if response.status_code >= 400:
            raise AdobeAPIError(f"Asset creation failed with {response.status_code}: {response.text[:200]}")
        payload = response.json()
        if "assetID" not in payload or "uploadUri" not in payload:
            raise AdobeAPIError("Asset creation response did not include assetID and uploadUri.")
        return payload

    def _upload_asset(self, upload_uri: str, pdf_path: Path) -> None:
        with pdf_path.open("rb") as handle:
            response = self.session.put(
                upload_uri,
                data=handle,
                headers={"Content-Type": "application/pdf"},
                timeout=120,
            )
        if response.status_code >= 400:
            raise AdobeAPIError(f"Asset upload failed with {response.status_code}: {response.text[:200]}")

    def _submit_job(self, access_token: str, asset_id: str) -> str:
        response = self.session.post(
            f"{self.base_url}/operation/accessibilitychecker",
            headers={**self._headers(access_token), "Content-Type": "application/json"},
            json={"assetID": asset_id},
            timeout=30,
        )
        if response.status_code >= 400:
            raise AdobeAPIError(f"Job submission failed with {response.status_code}: {response.text[:200]}")
        location = response.headers.get("location") or response.headers.get("Location")
        if not location:
            body_location = response.json().get("location") if response.content else None
            location = body_location
        if not location:
            raise AdobeAPIError("Accessibility checker submission did not return a polling location.")
        return location

    def _poll_for_result(self, access_token: str, location: str) -> dict[str, Any]:
        deadline = time.time() + self.poll_timeout
        url = location if location.startswith("http") else f"{self.base_url}{location}"

        while time.time() < deadline:
            response = self.session.get(url, headers=self._headers(access_token), timeout=30)
            if response.status_code >= 400:
                raise AdobeAPIError(f"Polling failed with {response.status_code}: {response.text[:200]}")

            payload = response.json() if response.content else {}
            status = str(payload.get("status", "")).lower()
            if status in {"done", "succeeded", "success"} or "result" in payload:
                return payload
            if status in {"failed", "error", "cancelled"}:
                raise AdobeAPIError(f"Adobe accessibility job failed with status {status}: {payload}")

            time.sleep(self.poll_interval)

        raise AdobeAPIError(f"Timed out polling Adobe job after {self.poll_timeout} seconds.")

    @staticmethod
    def _extract_report_download_url(payload: dict[str, Any]) -> str:
        report_node = payload.get("result", {}).get("report")
        if isinstance(report_node, dict):
            direct = report_node.get("downloadUri") or report_node.get("downloadURL")
            if isinstance(direct, str) and direct.startswith("http"):
                return direct

        report_node = payload.get("report")
        if isinstance(report_node, dict):
            direct = report_node.get("downloadUri") or report_node.get("downloadURL")
            if isinstance(direct, str) and direct.startswith("http"):
                return direct

        candidates: list[str] = []

        def walk(node: Any) -> None:
            if isinstance(node, dict):
                for key, value in node.items():
                    if key in {"downloadUri", "downloadURL", "uri", "url"} and isinstance(value, str):
                        candidates.append(value)
                    walk(value)
            elif isinstance(node, list):
                for item in node:
                    walk(item)

        report = payload.get("result", {}).get("report")
        if report:
            walk(report)
        if not candidates:
            walk(payload)

        for candidate in candidates:
            if candidate.startswith("http") and ("report" in candidate.lower() or candidate.lower().endswith(".json")):
                return candidate
        for candidate in candidates:
            if candidate.startswith("http"):
                return candidate
        raise AdobeAPIError("Could not locate a downloadable accessibility report URL in Adobe response.")

    def _map_report_to_rule_results(self, report: dict[str, Any]) -> dict[str, RuleResult]:
        summary = self._summarize_report(report)

        colour_result = self._to_rule_result(
            "colour_contrast_machine_check",
            self._make_check_result(summary.colour_status, summary.colour_evidence),
            "adobe",
            report,
        )
        reading_order_result = self._to_rule_result(
            "reading_order_machine_check",
            self._make_check_result(summary.reading_order_status, summary.reading_order_evidence),
            "adobe",
            report,
        )
        overall_result = self._to_rule_result(
            "adobe_full_check",
            self._make_check_result(summary.overall_status, summary.overall_evidence),
            "adobe",
            report,
        )

        return {
            "colour_contrast_machine_check": colour_result,
            "reading_order_machine_check": reading_order_result,
            "adobe_full_check": overall_result,
        }

    def _summarize_report(self, report: dict[str, Any]) -> AdobeReportSummary:
        findings = list(self._iter_findings(report))
        statuses = [self._normalize_status(self._value_for_key(finding, "status")) for finding in findings]
        overall_status = self._combine_statuses(statuses)

        overall_evidence = self._format_findings(findings) or ["Adobe accessibility report parsed successfully."]
        colour_findings = [
            finding
            for finding in findings
            if self._looks_like_colour_finding(finding)
        ]
        reading_order_findings = [
            finding
            for finding in findings
            if self._looks_like_reading_order_finding(finding)
        ]

        colour_status = self._combine_statuses(
            [self._normalize_status(self._value_for_key(finding, "status")) for finding in colour_findings]
        )
        reading_order_status = self._combine_statuses(
            [self._normalize_status(self._value_for_key(finding, "status")) for finding in reading_order_findings]
        )

        colour_evidence = self._format_findings(colour_findings) or ["Adobe report did not expose a discrete colour contrast finding."]
        reading_order_evidence = self._format_findings(reading_order_findings) or ["Adobe report did not expose a discrete reading order finding."]

        return AdobeReportSummary(
            raw_report=report,
            overall_status=overall_status,
            overall_evidence=overall_evidence,
            colour_status=colour_status,
            colour_evidence=colour_evidence,
            reading_order_status=reading_order_status,
            reading_order_evidence=reading_order_evidence,
        )

    @staticmethod
    def _value_for_key(data: dict[str, Any], *keys: str) -> Any:
        lowered = {str(key).lower(): value for key, value in data.items()}
        for key in keys:
            if key.lower() in lowered:
                return lowered[key.lower()]
        return None

    @staticmethod
    def _iter_findings(node: Any) -> Iterable[dict[str, Any]]:
        if isinstance(node, dict):
            keys = {str(key).lower() for key in node.keys()}
            if "status" in keys and ({"title", "name", "description", "message", "rule"} & keys):
                yield node
            for value in node.values():
                yield from AdobeClient._iter_findings(value)
        elif isinstance(node, list):
            for item in node:
                yield from AdobeClient._iter_findings(item)

    @staticmethod
    def _normalize_status(raw_status: Any) -> CheckStatus:
        value = str(raw_status or "").strip().lower()
        if value in {"pass", "passed", "success", "ok"}:
            return CheckStatus.PASS
        if value in {"fail", "failed", "error"}:
            return CheckStatus.FAIL
        if value in {"needs manual check", "manual", "needs_manual_review", "needs review"}:
            return CheckStatus.NEEDS_MANUAL_REVIEW
        return CheckStatus.NEEDS_MANUAL_REVIEW

    @staticmethod
    def _combine_statuses(statuses: list[CheckStatus]) -> CheckStatus:
        normalized = [status for status in statuses if status != CheckStatus.NA]
        if not normalized:
            return CheckStatus.NEEDS_MANUAL_REVIEW
        if CheckStatus.FAIL in normalized:
            return CheckStatus.FAIL
        if CheckStatus.NEEDS_MANUAL_REVIEW in normalized:
            return CheckStatus.NEEDS_MANUAL_REVIEW
        return CheckStatus.PASS

    @classmethod
    def _finding_text(cls, finding: dict[str, Any]) -> str:
        for key in ("title", "name", "rule", "description", "message"):
            value = cls._value_for_key(finding, key)
            if value:
                return str(value)
        return "Adobe finding"

    @classmethod
    def _format_findings(cls, findings: Iterable[dict[str, Any]]) -> list[str]:
        lines: list[str] = []
        for finding in findings:
            text = cls._finding_text(finding)
            status = cls._normalize_status(cls._value_for_key(finding, "status")).value
            lines.append(f"{text} [{status}]")
        return lines[:20]

    @classmethod
    def _looks_like_colour_finding(cls, finding: dict[str, Any]) -> bool:
        text = " ".join(
            str(cls._value_for_key(finding, key) or "")
            for key in ("title", "name", "rule", "description", "message")
        ).lower()
        return "contrast" in text or "color" in text or "colour" in text

    @classmethod
    def _looks_like_reading_order_finding(cls, finding: dict[str, Any]) -> bool:
        text = " ".join(
            str(cls._value_for_key(finding, key) or "")
            for key in ("title", "name", "rule", "description", "message")
        ).lower()
        return "reading order" in text or ("reading" in text and "order" in text)

    @staticmethod
    def _make_check_result(status: CheckStatus, evidence: list[str]):
        if status == CheckStatus.PASS:
            return pass_result(*evidence)
        if status == CheckStatus.FAIL:
            return fail_result(*evidence)
        return manual_result(*evidence)

    @staticmethod
    def _to_rule_result(rule_id: str, result, source: str, raw_report: dict[str, Any] | None) -> RuleResult:
        definition = RULE_DEFINITIONS[rule_id]
        status = result.status
        manual_review_reason = result.skipped_reason
        if status == CheckStatus.FAIL and definition.execution_mode != ExecutionMode.PYTHON_DETERMINISTIC:
            status = CheckStatus.NEEDS_MANUAL_REVIEW
            manual_review_reason = manual_review_reason or "This finding is not fully machine-verifiable and needs human review."
        confidence = 0.0 if status == CheckStatus.API_UNAVAILABLE else 0.8
        return RuleResult(
            rule_id=rule_id,
            theme=definition.theme,
            execution_mode=definition.execution_mode,
            status=status,
            evidence=result.details,
            remediation=definition.remediation_template,
            confidence=confidence,
            manual_review_reason=manual_review_reason,
            source=source,
            raw=raw_report,
        )
