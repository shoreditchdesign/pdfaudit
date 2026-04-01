from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import HTTPException

from app.core.config import Settings
from app.models.domain import (
    AdobeStatus,
    AuditRequest,
    AuditStartResponse,
    AuditStatusResponse,
    CheckStatus,
    DocumentAuditRecord,
    DocumentStage,
    DocumentStatus,
    ExecutionMode,
    GroupedResults,
    HealthResponse,
    JobCounts,
    JobStage,
    RetrievalCategory,
    RetrievalOutcome,
    RuleResult,
)
from app.services.adobe import AdobeClient
from app.services.adobe_cache import AdobeReportStore
from app.services.downloader import Downloader
from app.services.file_manager import FileManager
from app.services.layer1 import Layer1Orchestrator
from app.services.checks.pdf_utils import load_reader
from app.services.reporting import ReportBuilder, WorkbookTemplateResolver, compute_summary
from app.services.retrieval import RetrievalInspector
from app.services.rule_catalog import HSBC_POLICY_RULE_IDS, PDF_UA_RULE_IDS, RULE_DEFINITIONS, WCAG_RULE_IDS


@dataclass
class JobState:
    job_id: str
    use_adobe: bool
    stage: JobStage = JobStage.QUEUED
    cancelled: bool = False
    documents: list[DocumentStatus] = field(default_factory=list)
    records: list[DocumentAuditRecord] = field(default_factory=list)
    report_bytes: Optional[bytes] = None
    summary: object | None = None
    error: Optional[str] = None


class JobManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.file_manager = FileManager(settings.audit_temp_dir)
        self.downloader = Downloader()
        self.retrieval = RetrievalInspector()
        self.layer1 = Layer1Orchestrator()
        self.adobe_report_store = AdobeReportStore(settings.adobe_response_cache_dir)
        self.report_builder = ReportBuilder(
            WorkbookTemplateResolver(settings.audit_template_path),
            adobe_report_store=self.adobe_report_store,
        )
        self.jobs: dict[str, JobState] = {}

    def health(self) -> HealthResponse:
        configured = self.settings.adobe_configured
        return HealthResponse(
            status="ok",
            adobe=AdobeStatus(
                configured=configured,
                enabled=configured,
                message="Adobe credentials available." if configured else "Adobe credentials missing.",
            ),
        )

    def create_job(self, payload: AuditRequest) -> AuditStartResponse:
        urls = [str(url) for url in payload.urls]
        if len(urls) > self.settings.audit_max_batch_size:
            raise HTTPException(status_code=400, detail="Batch exceeds max size.")

        job_id = uuid4().hex
        self.jobs[job_id] = JobState(
            job_id=job_id,
            use_adobe=bool(payload.use_adobe),
            documents=[DocumentStatus(url=url, stage=DocumentStage.QUEUED) for url in urls],
        )
        loop = asyncio.get_running_loop()
        loop.create_task(self._run_job(self.jobs[job_id]))
        return AuditStartResponse(job_id=job_id)

    def get_status(self, job_id: str) -> AuditStatusResponse:
        state = self.jobs.get(job_id)
        if not state:
            raise HTTPException(status_code=404, detail="Job not found.")

        counts = JobCounts(
            total=len(state.documents),
            queued=sum(doc.stage == DocumentStage.QUEUED for doc in state.documents),
            running=sum(
                doc.stage in {DocumentStage.DOWNLOADING, DocumentStage.CHECKING, DocumentStage.REPORTING}
                for doc in state.documents
            ),
            completed=sum(doc.stage == DocumentStage.DONE for doc in state.documents),
            failed=sum(doc.stage == DocumentStage.FAILED for doc in state.documents),
            cancelled=sum(doc.stage == DocumentStage.CANCELLED for doc in state.documents),
        )
        return AuditStatusResponse(
            job_id=job_id,
            stage=state.stage,
            use_adobe=state.use_adobe,
            cancelled=state.cancelled,
            error=state.error,
            counts=counts,
            documents=state.documents,
            summary=state.summary,
            report_ready=state.report_bytes is not None,
        )

    def get_report(self, job_id: str) -> bytes:
        state = self.jobs.get(job_id)
        if not state:
            raise HTTPException(status_code=404, detail="Job not found.")
        if state.report_bytes is None:
            raise HTTPException(status_code=409, detail="Report not ready.")
        return state.report_bytes

    async def _run_job(self, state: JobState) -> None:
        state.stage = JobStage.RUNNING
        job_dir = self.file_manager.prepare_job_dir(state.job_id)
        semaphore = asyncio.Semaphore(self.settings.audit_max_concurrency)

        async def run_document(index: int, document: DocumentStatus) -> None:
            async with semaphore:
                await self._process_document(index, document, state, job_dir)

        try:
            await asyncio.gather(*(run_document(index, document) for index, document in enumerate(state.documents, start=1)))
            state.records.sort(key=lambda record: record.id)
            state.summary = compute_summary(state.records)
            state.report_bytes = self.report_builder.build(state.records, state.summary)
            state.stage = JobStage.COMPLETED
        except Exception as exc:
            state.stage = JobStage.FAILED
            state.error = str(exc)
        finally:
            self.file_manager.cleanup_job_dir(state.job_id)

    async def _process_document(self, index: int, document: DocumentStatus, state: JobState, job_dir: Path) -> None:
        try:
            document.stage = DocumentStage.DOWNLOADING
            retrieval = await asyncio.to_thread(self.retrieval.inspect, document.url)
            document.final_url = retrieval.final_url
            document.retrieval_category = retrieval.retrieval_category

            rule_results = self._base_rule_results()
            rule_results.update(self._retrieval_rule_results(retrieval))

            if retrieval.retrieval_category != RetrievalCategory.DIRECT_FILE_OK:
                record = self._record_from_results(index, document.url, retrieval, rule_results)
                state.records.append(record)
                document.stage = self._stage_for_result(record.overall_result)
                document.result = record.overall_result
                document.message = record.failure_summary or retrieval.message or "Document could not be audited automatically."
                return

            pdf_path = await asyncio.to_thread(
                self.downloader.download, retrieval.final_url or document.url, job_dir
            )
            document.stage = DocumentStage.CHECKING
            page_count = await asyncio.to_thread(lambda: len(load_reader(pdf_path).pages))

            rule_results.update(await asyncio.to_thread(self.layer1.run, pdf_path))
            adobe_client = AdobeClient(self.settings, enabled=state.use_adobe and self.settings.adobe_configured)
            adobe_results = await asyncio.to_thread(adobe_client.check_document, str(pdf_path))
            rule_results.update(adobe_results)
            adobe_raw = adobe_results.get("adobe_full_check").raw if adobe_results.get("adobe_full_check") else None
            if adobe_raw:
                await asyncio.to_thread(self.adobe_report_store.save, document.url, adobe_raw)
                if retrieval.final_url and retrieval.final_url != document.url:
                    await asyncio.to_thread(self.adobe_report_store.save, retrieval.final_url, adobe_raw)

            document.stage = DocumentStage.REPORTING
            record = self._record_from_results(index, document.url, retrieval, rule_results, page_count=page_count)
            state.records.append(record)
            document.stage = DocumentStage.DONE
            document.result = record.overall_result
            document.message = "Audit completed."
        except Exception as exc:
            retrieval = RetrievalOutcome(
                original_url=document.url,
                final_url=document.url,
                retrieval_category=RetrievalCategory.REQUEST_ERROR,
                message=f"Audit failed: {exc}",
            )
            rule_results = self._base_rule_results()
            rule_results.update(
                self._retrieval_rule_results(
                    retrieval,
                    error_message=f"Unexpected audit error: {exc}",
                )
            )
            record = self._record_from_results(index, document.url, retrieval, rule_results)
            state.records.append(record)
            document.stage = DocumentStage.FAILED
            document.result = CheckStatus.FAIL
            document.message = f"Audit failed: {exc}"

    @staticmethod
    def _stage_for_result(result: CheckStatus) -> DocumentStage:
        return DocumentStage.FAILED if result == CheckStatus.FAIL else DocumentStage.DONE

    def _record_from_results(
        self,
        index: int,
        original_url: str,
        retrieval: RetrievalOutcome,
        rule_results: dict[str, RuleResult],
        page_count: int | None = None,
    ) -> DocumentAuditRecord:
        grouped_results = GroupedResults(
            pdf_ua_result=self._derive_bucket_result(PDF_UA_RULE_IDS, rule_results),
            wcag_result=self._derive_wcag_bucket_result(rule_results),
            hsbc_policy_result=self._derive_bucket_result(HSBC_POLICY_RULE_IDS, rule_results),
        )
        overall_result = self._derive_overall_result(grouped_results)

        return DocumentAuditRecord(
            id=index,
            original_url=original_url,
            final_url=retrieval.final_url,
            http_status=str(retrieval.http_status or ""),
            retrieval_category=retrieval.retrieval_category,
            content_type=retrieval.content_type,
            redirect_count=retrieval.redirect_count,
            page_title=retrieval.page_title,
            page_count=page_count,
            overall_result=overall_result,
            grouped_results=grouped_results,
            rule_results=rule_results,
            failure_summary=self._failure_summary(rule_results),
            failure_detail=self._failure_detail(rule_results),
            remediation_guidance=self._remediation_guidance(rule_results),
            manual_review_summary=self._manual_review_summary(rule_results),
            notes=self._notes(retrieval, rule_results),
        )

    @staticmethod
    def _derive_overall_result(grouped_results: GroupedResults) -> CheckStatus:
        statuses = [
            grouped_results.pdf_ua_result,
            grouped_results.wcag_result,
            grouped_results.hsbc_policy_result,
        ]
        statuses = [status for status in statuses if status != CheckStatus.NA]
        if CheckStatus.FAIL in statuses:
            return CheckStatus.FAIL
        if CheckStatus.NEEDS_MANUAL_REVIEW in statuses:
            return CheckStatus.NEEDS_MANUAL_REVIEW
        if CheckStatus.API_UNAVAILABLE in statuses:
            return CheckStatus.NEEDS_MANUAL_REVIEW
        return CheckStatus.PASS

    @staticmethod
    def _derive_bucket_result(rule_ids: set[str], rule_results: dict[str, RuleResult]) -> CheckStatus:
        statuses = [rule_results[rule_id].status for rule_id in rule_ids if rule_id in rule_results]
        statuses = [status for status in statuses if status != CheckStatus.NA]
        if not statuses:
            return CheckStatus.NA
        if CheckStatus.FAIL in statuses:
            return CheckStatus.FAIL
        if CheckStatus.NEEDS_MANUAL_REVIEW in statuses or CheckStatus.API_UNAVAILABLE in statuses:
            return CheckStatus.NEEDS_MANUAL_REVIEW
        return CheckStatus.PASS

    @staticmethod
    def _derive_wcag_bucket_result(rule_results: dict[str, RuleResult]) -> CheckStatus:
        statuses = [rule_results[rule_id].status for rule_id in WCAG_RULE_IDS if rule_id in rule_results]
        statuses = [status for status in statuses if status != CheckStatus.NA]
        if not statuses:
            return CheckStatus.NA

        if CheckStatus.FAIL in statuses:
            return CheckStatus.FAIL

        adobe_statuses = {
            rule_results[rule_id].status
            for rule_id in {"colour_contrast_machine_check", "reading_order_machine_check", "adobe_full_check"}
            if rule_id in rule_results
        }
        if CheckStatus.API_UNAVAILABLE in adobe_statuses:
            return CheckStatus.API_UNAVAILABLE
        if CheckStatus.NEEDS_MANUAL_REVIEW in adobe_statuses:
            return CheckStatus.NEEDS_MANUAL_REVIEW

        retrieval_statuses = {
            rule_results[rule_id].status
            for rule_id in {"url_resolves", "url_is_expected_file", "extractable_text_present"}
            if rule_id in rule_results
        }
        if CheckStatus.NEEDS_MANUAL_REVIEW in retrieval_statuses:
            return CheckStatus.NEEDS_MANUAL_REVIEW
        if CheckStatus.API_UNAVAILABLE in retrieval_statuses:
            return CheckStatus.API_UNAVAILABLE

        return CheckStatus.PASS

    @staticmethod
    def _ordered_findings(rule_results: dict[str, RuleResult]) -> list[RuleResult]:
        findings = [
            result
            for result in rule_results.values()
            if result.status in {CheckStatus.FAIL, CheckStatus.NEEDS_MANUAL_REVIEW, CheckStatus.API_UNAVAILABLE}
        ]
        return sorted(findings, key=lambda result: (result.theme.value, result.rule_id))

    @classmethod
    def _failure_summary(cls, rule_results: dict[str, RuleResult]) -> str:
        titles = [RULE_DEFINITIONS[result.rule_id].title for result in cls._ordered_findings(rule_results)]
        return ", ".join(titles)

    @classmethod
    def _failure_detail(cls, rule_results: dict[str, RuleResult]) -> str:
        details: list[str] = []
        for result in cls._ordered_findings(rule_results):
            title = RULE_DEFINITIONS[result.rule_id].title
            evidence = "; ".join(result.evidence) if result.evidence else "No detailed evidence captured."
            details.append(f"{title}: {evidence}")
        return " | ".join(details)

    @classmethod
    def _remediation_guidance(cls, rule_results: dict[str, RuleResult]) -> str:
        guidance: list[str] = []
        for result in cls._ordered_findings(rule_results):
            if result.remediation:
                guidance.append(f"{RULE_DEFINITIONS[result.rule_id].title}: {result.remediation}")
        return " | ".join(guidance)

    @classmethod
    def _manual_review_summary(cls, rule_results: dict[str, RuleResult]) -> str:
        notes: list[str] = []
        for result in cls._ordered_findings(rule_results):
            if result.status == CheckStatus.NEEDS_MANUAL_REVIEW or result.manual_review_reason:
                title = RULE_DEFINITIONS[result.rule_id].title
                reason = result.manual_review_reason or "Requires human verification."
                notes.append(f"{title}: {reason}")
        return " | ".join(notes)

    @staticmethod
    def _notes(retrieval: RetrievalOutcome, rule_results: dict[str, RuleResult]) -> str:
        notes = [retrieval.message] if retrieval.message else []
        for result in rule_results.values():
            if result.raw:
                notes.append(f"{result.rule_id} has raw evidence payload.")
        return " | ".join(notes)

    @staticmethod
    def _base_rule_results() -> dict[str, RuleResult]:
        return {
            rule_id: RuleResult(
                rule_id=rule_id,
                theme=definition.theme,
                execution_mode=definition.execution_mode,
                status=CheckStatus.NA,
                remediation=definition.remediation_template,
                confidence=0.0,
                source="system",
            )
            for rule_id, definition in RULE_DEFINITIONS.items()
        }

    def _retrieval_rule_results(
        self,
        retrieval: RetrievalOutcome,
        error_message: str | None = None,
    ) -> dict[str, RuleResult]:
        message = error_message or retrieval.message or "URL inspection completed."
        evidence = [message]
        if retrieval.final_url and retrieval.final_url != retrieval.original_url:
            evidence.append(f"Final destination: {retrieval.final_url}")
        if retrieval.page_title:
            evidence.append(f"Page title: {retrieval.page_title}")

        url_resolves_status = CheckStatus.PASS
        expected_file_status = CheckStatus.PASS
        landing_status = CheckStatus.NA
        landing_reason: Optional[str] = None

        if retrieval.retrieval_category in {RetrievalCategory.HARD_404, RetrievalCategory.REQUEST_ERROR}:
            url_resolves_status = CheckStatus.FAIL
            expected_file_status = CheckStatus.FAIL
        elif retrieval.retrieval_category == RetrievalCategory.SOFT_404:
            url_resolves_status = CheckStatus.FAIL
            expected_file_status = CheckStatus.FAIL
            landing_status = CheckStatus.NEEDS_MANUAL_REVIEW
            landing_reason = "Redirect appears to land on a not-found or generic replacement page."
        elif retrieval.retrieval_category in {
            RetrievalCategory.ALT_LANDING_PAGE_NON_PDF,
            RetrievalCategory.REVIEW_REQUIRED,
        }:
            expected_file_status = CheckStatus.NEEDS_MANUAL_REVIEW
            landing_status = CheckStatus.NEEDS_MANUAL_REVIEW
            if retrieval.retrieval_category == RetrievalCategory.REVIEW_REQUIRED:
                landing_reason = (
                    "Destination is a non-PDF office file and should be reviewed with the "
                    "correct format-specific audit path."
                )
            else:
                landing_reason = "Destination is not a direct PDF and may require business review."

        return {
            "url_resolves": RuleResult(
                rule_id="url_resolves",
                theme=RULE_DEFINITIONS["url_resolves"].theme,
                execution_mode=ExecutionMode.PYTHON_DETERMINISTIC,
                status=url_resolves_status,
                evidence=evidence,
                remediation=RULE_DEFINITIONS["url_resolves"].remediation_template,
                confidence=1.0,
                source="python",
            ),
            "url_is_expected_file": RuleResult(
                rule_id="url_is_expected_file",
                theme=RULE_DEFINITIONS["url_is_expected_file"].theme,
                execution_mode=ExecutionMode.PYTHON_DETERMINISTIC,
                status=expected_file_status,
                evidence=evidence,
                remediation=RULE_DEFINITIONS["url_is_expected_file"].remediation_template,
                confidence=1.0 if expected_file_status != CheckStatus.NEEDS_MANUAL_REVIEW else 0.7,
                manual_review_reason=landing_reason,
                source="python",
            ),
            "unexpected_landing_page": RuleResult(
                rule_id="unexpected_landing_page",
                theme=RULE_DEFINITIONS["unexpected_landing_page"].theme,
                execution_mode=ExecutionMode.PYTHON_HEURISTIC,
                status=landing_status,
                evidence=evidence if landing_status != CheckStatus.NA else [],
                remediation=RULE_DEFINITIONS["unexpected_landing_page"].remediation_template,
                confidence=0.75 if landing_status != CheckStatus.NA else 0.0,
                manual_review_reason=landing_reason,
                source="python",
            ),
        }
