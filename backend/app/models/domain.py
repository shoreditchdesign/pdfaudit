from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


class CheckStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NEEDS_MANUAL_REVIEW = "NEEDS_MANUAL_REVIEW"
    API_UNAVAILABLE = "API_UNAVAILABLE"
    NA = "N/A"


class ExecutionMode(str, Enum):
    PYTHON_DETERMINISTIC = "python_deterministic"
    PYTHON_HEURISTIC = "python_heuristic"
    ADOBE_API = "adobe_api"
    MANUAL = "manual_review"


class RuleTheme(str, Enum):
    URL_RETRIEVAL = "url_retrieval"
    METADATA = "metadata"
    SECURITY = "security"
    SCAN_DETECTION = "scan_detection"
    STRUCTURE = "structure"
    HEADINGS = "headings"
    ALT_TEXT = "alt_text"
    NAVIGATION = "navigation"
    TOC = "toc"
    LISTS = "lists"
    TABLES = "tables"
    LINKS = "links"
    FORMS = "forms"
    FOOTNOTES = "footnotes"
    VISUAL_ACCESSIBILITY = "visual_accessibility"


class RetrievalCategory(str, Enum):
    DIRECT_FILE_OK = "DIRECT_FILE_OK"
    HARD_404 = "HARD_404"
    SOFT_404 = "SOFT_404"
    ALT_LANDING_PAGE_NON_PDF = "ALT_LANDING_PAGE_NON_PDF"
    REQUEST_ERROR = "REQUEST_ERROR"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class DocumentStage(str, Enum):
    QUEUED = "QUEUED"
    DOWNLOADING = "DOWNLOADING"
    CHECKING = "CHECKING"
    REPORTING = "REPORTING"
    DONE = "DONE"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class JobStage(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class RuleDefinition(BaseModel):
    rule_id: str
    theme: RuleTheme
    title: str
    execution_mode: ExecutionMode
    severity: str = "medium"
    remediation_template: str


class CheckResult(BaseModel):
    status: CheckStatus
    details: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)
    skipped_reason: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


class RuleResult(BaseModel):
    rule_id: str
    theme: RuleTheme
    execution_mode: ExecutionMode
    status: CheckStatus
    evidence: List[str] = Field(default_factory=list)
    remediation: str = ""
    confidence: float = 1.0
    manual_review_reason: Optional[str] = None
    source: str = "python"
    raw: Optional[Dict[str, Any]] = None


class RetrievalOutcome(BaseModel):
    original_url: str
    final_url: str
    http_status: Optional[int] = None
    redirect_count: int = 0
    content_type: str = ""
    page_title: str = ""
    body_snippet: str = ""
    retrieval_category: RetrievalCategory
    message: str = ""


class GroupedResults(BaseModel):
    pdf_ua_result: CheckStatus
    wcag_result: CheckStatus
    hsbc_policy_result: CheckStatus


class DocumentAuditRecord(BaseModel):
    id: int
    source_row_number: Optional[int] = None
    pdf_name: Optional[str] = None
    original_url: str
    final_url: str = ""
    http_status: str = ""
    retrieval_category: RetrievalCategory
    content_type: str = ""
    redirect_count: int = 0
    page_title: str = ""
    page_count: Optional[int] = None
    overall_result: CheckStatus
    grouped_results: GroupedResults
    rule_results: Dict[str, RuleResult]
    failure_summary: str = ""
    failure_detail: str = ""
    remediation_guidance: str = ""
    manual_review_summary: str = ""
    notes: str = ""


class SummaryMetrics(BaseModel):
    total: int = 0
    pass_count: int = 0
    fail_count: int = 0
    manual_review_count: int = 0
    unreachable_count: int = 0
    run_timestamp: datetime
    per_rule_failures: Dict[str, int] = Field(default_factory=dict)


class AuditRequest(BaseModel):
    urls: List[HttpUrl]
    use_adobe: Optional[bool] = True


class AuditStartResponse(BaseModel):
    job_id: str


class AdobeStatus(BaseModel):
    configured: bool
    enabled: bool
    message: str


class HealthResponse(BaseModel):
    status: str
    adobe: AdobeStatus


class DocumentStatus(BaseModel):
    url: str
    stage: DocumentStage
    result: Optional[CheckStatus] = None
    message: Optional[str] = None
    final_url: Optional[str] = None
    retrieval_category: Optional[RetrievalCategory] = None


class JobCounts(BaseModel):
    total: int
    queued: int
    running: int
    completed: int
    failed: int
    cancelled: int


class AuditStatusResponse(BaseModel):
    job_id: str
    stage: JobStage
    use_adobe: bool
    cancelled: bool = False
    error: Optional[str] = None
    counts: JobCounts
    documents: List[DocumentStatus]
    summary: Optional[SummaryMetrics] = None
    report_ready: bool = False
