from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import warnings
from collections import Counter
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Iterable


def suppress_runtime_noise() -> None:
    os.environ.setdefault("PYTHONWARNINGS", "ignore")
    warnings.filterwarnings("ignore", category=Warning, message="urllib3 v2 only supports OpenSSL 1.1.1+.*")
    warnings.filterwarnings("ignore", message=".*Ignoring wrong pointing object.*")
    try:
        from urllib3.exceptions import NotOpenSSLWarning

        warnings.filterwarnings("ignore", category=NotOpenSSLWarning)
    except Exception:
        pass

    logging.getLogger("pypdf").setLevel(logging.ERROR)
    logging.getLogger("pypdf._reader").setLevel(logging.ERROR)
    logging.getLogger("urllib3").setLevel(logging.ERROR)


suppress_runtime_noise()

from app.core.config import get_settings
from app.models.domain import AuditRequest, CheckStatus, DocumentStage, RetrievalCategory
from app.services.audit_job_service import JobManager


def derive_theme_name(path: Path) -> str:
    stem = path.stem.strip()
    if stem.startswith("audit-"):
        stem = stem[len("audit-") :]
    sanitized = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in stem.lower())
    sanitized = sanitized.strip("-_")
    return sanitized or "default"


def parse_links_file(path: Path) -> list[str]:
    urls: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        urls.append(value)
    return urls


def display_name_from_url(url: str) -> str:
    candidate = Path(url.split("?", 1)[0]).name or url.rsplit("/", 1)[-1]
    candidate = candidate.removesuffix(".pdf").removesuffix(".docx").removesuffix(".xlsx").removesuffix(".xls")
    candidate = candidate.strip().strip('"').strip("'")
    candidate = re.sub(r"[-_]+", " ", candidate)
    candidate = re.sub(r"\s+", " ", candidate).strip()
    return candidate.title() if candidate else url


def pretty_status(status: CheckStatus) -> str:
    mapping = {
        CheckStatus.PASS: "Pass",
        CheckStatus.FAIL: "Fail",
        CheckStatus.NEEDS_MANUAL_REVIEW: "Needs Review",
        CheckStatus.API_UNAVAILABLE: "Pending Adobe",
        CheckStatus.NA: "N/A",
    }
    return mapping.get(status, status.value.replace("_", " ").title())


def format_record_update(record, total: int) -> str:
    name = display_name_from_url(record.original_url)
    prefix = f"[{record.id}/{total}]"

    if record.retrieval_category != RetrievalCategory.DIRECT_FILE_OK:
        message = record.notes or record.failure_summary or record.retrieval_category.value.replace("_", " ").title()
        if record.retrieval_category == RetrievalCategory.REVIEW_REQUIRED:
            return f"○ {prefix} REVIEW: \"{name}\" - non-PDF source, use the correct format-specific audit path"
        return f"✕ {prefix} BLOCKED: \"{name}\" - {message}"

    if record.overall_result == CheckStatus.PASS:
        return (
            f"✓ {prefix} PASSED: \"{name}\" - "
            f"PDF/UA: {pretty_status(record.grouped_results.pdf_ua_result)} | "
            f"WCAG: {pretty_status(record.grouped_results.wcag_result)}"
        )

    if record.overall_result == CheckStatus.NEEDS_MANUAL_REVIEW:
        return (
            f"○ {prefix} REVIEW: \"{name}\" - "
            f"PDF/UA: {pretty_status(record.grouped_results.pdf_ua_result)} | "
            f"WCAG: {pretty_status(record.grouped_results.wcag_result)}"
        )

    detail = record.failure_summary or "Machine-detectable issues were found"
    return (
        f"✕ {prefix} FLAGGED: \"{name}\" - "
        f"PDF/UA: {pretty_status(record.grouped_results.pdf_ua_result)} | "
        f"WCAG: {pretty_status(record.grouped_results.wcag_result)} | "
        f"{detail}"
    )


def print_completion_summary(manager: JobManager, job_id: str, elapsed_seconds: float) -> None:
    state = manager.jobs[job_id]
    records = state.records
    total = len(records)
    pass_count = sum(record.overall_result == CheckStatus.PASS for record in records)
    fail_count = sum(record.overall_result == CheckStatus.FAIL for record in records)
    review_count = sum(record.overall_result == CheckStatus.NEEDS_MANUAL_REVIEW for record in records)
    pending_adobe_count = sum(record.grouped_results.wcag_result == CheckStatus.API_UNAVAILABLE for record in records)
    blocked_count = sum(record.retrieval_category != RetrievalCategory.DIRECT_FILE_OK for record in records)
    error_count = sum(doc.stage == DocumentStage.FAILED for doc in state.documents)
    rate = (total / elapsed_seconds) if elapsed_seconds > 0 else 0.0

    print()
    print("AUDIT COMPLETE")
    print(
        f"Total: {total}  | Passed: {pass_count}  | Failed: {fail_count}  | "
        f"Needs Review: {review_count}  | Pending Adobe: {pending_adobe_count}  | "
        f"Blocked: {blocked_count}  | Errors: {error_count}  | "
        f"Time: {elapsed_seconds:.1f}s  | Rate: {rate:.2f}/s"
    )


def summarize_workbook_rows(manager: JobManager, job_id: str) -> dict[str, object]:
    state = manager.jobs[job_id]
    records = state.records
    pdfua_counts = Counter(record.grouped_results.pdf_ua_result.value for record in records)
    wcag_counts = Counter(record.grouped_results.wcag_result.value for record in records)
    retrieval_counts = Counter(record.retrieval_category.value for record in records)
    adobe_counts = Counter(
        "Complete"
        if record.rule_results["adobe_full_check"].status.value not in {"N/A", "API_UNAVAILABLE"}
        else "Not Started"
        for record in records
    )
    return {
        "records": len(records),
        "pdf_ua": dict(pdfua_counts),
        "wcag": dict(wcag_counts),
        "retrieval": dict(retrieval_counts),
        "adobe": dict(adobe_counts),
    }


async def run_audit(
    urls: Iterable[str],
    theme: str,
    reports_dir: Path,
    summary_dir: Path,
    concurrency: int | None,
    poll_timeout: int | None,
    poll_interval: float | None,
) -> tuple[Path, Path]:
    settings = get_settings()
    urls = list(urls)
    settings.audit_max_batch_size = max(settings.audit_max_batch_size, len(urls))
    if concurrency is not None:
        settings.audit_max_concurrency = concurrency
    if poll_timeout is not None:
        settings.adobe_poll_timeout_seconds = poll_timeout
    if poll_interval is not None:
        settings.adobe_poll_interval_seconds = poll_interval

    reports_dir.mkdir(parents=True, exist_ok=True)
    summary_dir.mkdir(parents=True, exist_ok=True)

    manager = JobManager(settings)
    start = manager.create_job(AuditRequest(urls=urls, use_adobe=True))
    job_id = start.job_id
    started_at = perf_counter()
    emitted_ids: set[int] = set()

    print(f"Starting audit for \"{theme}\" ({len(urls)} links)...")
    print(
        f"Adobe enabled | Concurrency: {settings.audit_max_concurrency} | "
        f"Poll timeout: {settings.adobe_poll_timeout_seconds}s | "
        f"Poll interval: {settings.adobe_poll_interval_seconds}s"
    )
    print()
    while True:
        status = manager.get_status(job_id)
        state = manager.jobs[job_id]
        for record in sorted(state.records, key=lambda item: item.id):
            if record.id in emitted_ids:
                continue
            print(format_record_update(record, len(urls)), flush=True)
            emitted_ids.add(record.id)
        if status.stage.value in {"COMPLETED", "FAILED", "CANCELLED"}:
            break
        await asyncio.sleep(1)

    state = manager.jobs[job_id]
    if state.error:
        raise RuntimeError(state.error)

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    report_path = reports_dir / f"audit-{theme}-{timestamp}.xlsx"
    report_path.write_bytes(manager.get_report(job_id))

    summary_payload = {
        "job_id": job_id,
        "timestamp": timestamp,
        "theme": theme,
        "report_path": str(report_path),
        "source_count": len(urls),
        "summary": summarize_workbook_rows(manager, job_id),
    }
    summary_path = summary_dir / f"audit-{theme}-{timestamp}.json"
    summary_path.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")
    elapsed_seconds = perf_counter() - started_at
    print_completion_summary(manager, job_id, elapsed_seconds)
    print(f"Workbook: {report_path}")
    print(f"Summary:  {summary_path}")
    return report_path, summary_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the PDF audit from a plain-text links file.")
    parser.add_argument(
        "links_file",
        nargs="?",
        default="target/audit-default.txt",
        help="Path to a text file containing one URL per line.",
    )
    parser.add_argument("--reports-dir", default="reports", help="Directory for workbook outputs.")
    parser.add_argument("--summary-dir", default="summary", help="Directory for JSON summaries.")
    parser.add_argument("--concurrency", type=int, default=None, help="Override audit concurrency.")
    parser.add_argument("--poll-timeout", type=int, default=None, help="Override Adobe poll timeout in seconds.")
    parser.add_argument("--poll-interval", type=float, default=None, help="Override Adobe poll interval in seconds.")
    args = parser.parse_args()

    links_path = Path(args.links_file)
    if not links_path.exists():
        raise SystemExit(f"Links file not found: {links_path}")

    urls = parse_links_file(links_path)
    if not urls:
        raise SystemExit(f"No URLs found in links file: {links_path}")
    theme = derive_theme_name(links_path)

    asyncio.run(
        run_audit(
            urls=urls,
            theme=theme,
            reports_dir=Path(args.reports_dir),
            summary_dir=Path(args.summary_dir),
            concurrency=args.concurrency,
            poll_timeout=args.poll_timeout,
            poll_interval=args.poll_interval,
        )
    )


if __name__ == "__main__":
    main()
