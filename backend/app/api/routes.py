from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.core.config import Settings, get_settings
from app.models.domain import AuditRequest, AuditStartResponse, AuditStatusResponse, HealthResponse
from app.services.audit_job_service import JobManager


router = APIRouter()
_job_managers: dict[str, JobManager] = {}


def get_job_manager(settings: Settings = Depends(get_settings)) -> JobManager:
    key = str(settings.audit_temp_dir)
    if key not in _job_managers:
        _job_managers[key] = JobManager(settings)
    return _job_managers[key]


@router.get("/health", response_model=HealthResponse)
def health(job_manager: JobManager = Depends(get_job_manager)) -> HealthResponse:
    return job_manager.health()


@router.post("/audit", response_model=AuditStartResponse)
async def start_audit(
    payload: AuditRequest, job_manager: JobManager = Depends(get_job_manager)
) -> AuditStartResponse:
    return job_manager.create_job(payload)


@router.get("/audit/{job_id}/status", response_model=AuditStatusResponse)
def audit_status(job_id: str, job_manager: JobManager = Depends(get_job_manager)) -> AuditStatusResponse:
    return job_manager.get_status(job_id)


@router.get("/audit/{job_id}/report")
def audit_report(job_id: str, job_manager: JobManager = Depends(get_job_manager)) -> Response:
    report_bytes = job_manager.get_report(job_id)
    headers = {"Content-Disposition": f'attachment; filename="audit-{job_id}.xlsx"'}
    return Response(
        content=report_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )
