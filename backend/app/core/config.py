from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


_CURRENT_FILE = Path(__file__).resolve()
_BACKEND_DIR = _CURRENT_FILE.parents[2]
_ROOT_DIR = _CURRENT_FILE.parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(_BACKEND_DIR / ".env"), str(_ROOT_DIR / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    adobe_client_id: Optional[str] = Field(default=None, alias="ADOBE_CLIENT_ID")
    adobe_client_secret: Optional[str] = Field(default=None, alias="ADOBE_CLIENT_SECRET")
    adobe_scope: Optional[str] = Field(default=None, alias="ADOBE_SCOPE")
    adobe_region: str = Field(default="ue1", alias="ADOBE_REGION")
    adobe_base_url: Optional[str] = Field(default=None, alias="ADOBE_BASE_URL")
    adobe_poll_interval_seconds: float = Field(default=2.0, alias="ADOBE_POLL_INTERVAL_SECONDS")
    adobe_poll_timeout_seconds: int = Field(default=90, alias="ADOBE_POLL_TIMEOUT_SECONDS")
    audit_template_path: Optional[Path] = Field(default=None, alias="AUDIT_TEMPLATE_PATH")
    audit_sample_pdf_dir: Optional[Path] = Field(default=None, alias="AUDIT_SAMPLE_PDF_DIR")
    audit_max_batch_size: int = Field(default=100, alias="AUDIT_MAX_BATCH_SIZE")
    audit_max_concurrency: int = Field(default=5, alias="AUDIT_MAX_CONCURRENCY")
    audit_temp_dir: Path = Field(default=Path("/tmp/hsbc_audit"), alias="AUDIT_TEMP_DIR")
    adobe_response_cache_dir: Path = Field(
        default=_ROOT_DIR / "docs" / "artifacts" / "adobe_cache",
        alias="ADOBE_RESPONSE_CACHE_DIR",
    )

    @property
    def adobe_configured(self) -> bool:
        return bool(self.adobe_client_id and self.adobe_client_secret)

    @property
    def adobe_pdf_services_base_url(self) -> str:
        if self.adobe_base_url:
            return self.adobe_base_url.rstrip("/")
        if self.adobe_region == "ue1":
            return "https://pdf-services.adobe.io"
        return f"https://pdf-services-{self.adobe_region}.adobe.io"


@lru_cache
def get_settings() -> Settings:
    return Settings()
