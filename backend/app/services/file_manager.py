from __future__ import annotations

import shutil
from pathlib import Path


class FileManager:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir

    def prepare_job_dir(self, job_id: str) -> Path:
        job_dir = self.base_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        return job_dir

    def cleanup_job_dir(self, job_id: str) -> None:
        shutil.rmtree(self.base_dir / job_id, ignore_errors=True)

