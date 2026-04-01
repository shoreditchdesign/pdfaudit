from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class AdobeReportStore:
    def __init__(self, root_dir: Path | None) -> None:
        self.root_dir = root_dir

    def save(self, url: str, raw_report: dict[str, Any] | None) -> Path | None:
        if not self.root_dir or not url or not raw_report:
            return None
        self.root_dir.mkdir(parents=True, exist_ok=True)
        path = self._path_for_url(url)
        payload = {
            "url": url,
            "raw_report": raw_report,
        }
        path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
        return path

    def load(self, url: str) -> dict[str, Any] | None:
        if not self.root_dir or not url:
            return None
        path = self._path_for_url(url)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        raw_report = payload.get("raw_report")
        return raw_report if isinstance(raw_report, dict) else None

    def _path_for_url(self, url: str) -> Path:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self.root_dir / f"{digest}.json"
