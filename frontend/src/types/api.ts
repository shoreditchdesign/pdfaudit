export type CheckStatus =
  | "PASS"
  | "FAIL"
  | "NEEDS_MANUAL_REVIEW"
  | "API_UNAVAILABLE"
  | "N/A";

export type JobStage = "QUEUED" | "RUNNING" | "COMPLETED" | "FAILED" | "CANCELLED";

export type DocumentStage =
  | "QUEUED"
  | "DOWNLOADING"
  | "CHECKING"
  | "REPORTING"
  | "DONE"
  | "FAILED"
  | "CANCELLED";

export interface HealthResponse {
  status: string;
  adobe: {
    configured: boolean;
    enabled: boolean;
    message: string;
  };
}

export interface AuditStartResponse {
  job_id: string;
}

export interface AuditDocumentStatus {
  url: string;
  stage: DocumentStage;
  result?: CheckStatus | null;
  message?: string | null;
}

export interface AuditStatusResponse {
  job_id: string;
  stage: JobStage;
  use_adobe: boolean;
  cancelled: boolean;
  report_ready: boolean;
  error?: string | null;
  counts: {
    total: number;
    queued: number;
    running: number;
    completed: number;
    failed: number;
    cancelled: number;
  };
  documents: AuditDocumentStatus[];
  summary?: {
    total: number;
    pass_count: number;
    fail_count: number;
    manual_review_count: number;
    unreachable_count: number;
    run_timestamp: string;
    per_check_failures: Record<string, number>;
  } | null;
}
