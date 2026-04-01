from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import requests


class Downloader:
    def head(self, url: str) -> requests.Response:
        response = requests.head(url, allow_redirects=True, timeout=15)
        if response.status_code in {403, 405} or not response.headers.get("Content-Type"):
            fallback = requests.get(url, allow_redirects=True, timeout=30, stream=True)
            fallback.close()
            return fallback
        return response

    def download(self, url: str, destination_dir: Path) -> Path:
        response = requests.get(url, allow_redirects=True, timeout=60)
        response.raise_for_status()
        filename = Path(urlparse(url).path).name or "downloaded.pdf"
        target = destination_dir / filename
        target.write_bytes(response.content)
        return target
