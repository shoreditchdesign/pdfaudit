from __future__ import annotations

from html import unescape
import re

import requests

from app.models.domain import RetrievalCategory, RetrievalOutcome


class RetrievalInspector:
    NOTFOUND_PATTERNS = ("/notfound-404", "/404", "notfound-404", "page not found", "not found")
    TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
    TAG_RE = re.compile(r"<[^>]+>")
    WS_RE = re.compile(r"\s+")

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "pdfaudit-retrieval/1.0"})

    def inspect(self, url: str) -> RetrievalOutcome:
        try:
            response = self.session.get(url, allow_redirects=True, timeout=15, stream=True)
        except requests.RequestException as exc:
            return RetrievalOutcome(
                original_url=url,
                final_url="",
                retrieval_category=RetrievalCategory.REQUEST_ERROR,
                message=str(exc),
            )

        final_url = response.url
        status = response.status_code
        content_type = response.headers.get("Content-Type", "")
        redirect_count = len(response.history)
        title = ""
        body_snippet = ""

        if "html" in content_type.lower():
            try:
                text = response.text[:25000]
                title, body_snippet = self._extract_html_signals(text)
            except Exception:
                pass

        response.close()

        category = self._classify(status, final_url, content_type, title, body_snippet)
        message = self._message_for(category)
        return RetrievalOutcome(
            original_url=url,
            final_url=final_url,
            http_status=status,
            redirect_count=redirect_count,
            content_type=content_type,
            page_title=title,
            body_snippet=body_snippet,
            retrieval_category=category,
            message=message,
        )

    def _extract_html_signals(self, text: str) -> tuple[str, str]:
        title_match = self.TITLE_RE.search(text)
        title = unescape(title_match.group(1)).strip() if title_match else ""
        body = self.TAG_RE.sub(" ", text)
        body = unescape(self.WS_RE.sub(" ", body)).strip()
        return title[:300], body[:300]

    def _classify(
        self, status: int, final_url: str, content_type: str, title: str, body_snippet: str
    ) -> RetrievalCategory:
        final_lower = final_url.lower()
        title_lower = title.lower()
        body_lower = body_snippet.lower()

        if status == 404:
            return RetrievalCategory.HARD_404
        if any(pattern in final_lower for pattern in self.NOTFOUND_PATTERNS):
            return RetrievalCategory.SOFT_404
        if "html" in content_type.lower() and any(pattern in title_lower for pattern in self.NOTFOUND_PATTERNS):
            return RetrievalCategory.SOFT_404
        if "html" in content_type.lower() and any(pattern in body_lower for pattern in self.NOTFOUND_PATTERNS):
            return RetrievalCategory.SOFT_404
        if "pdf" in content_type.lower():
            return RetrievalCategory.DIRECT_FILE_OK
        if "html" in content_type.lower():
            return RetrievalCategory.ALT_LANDING_PAGE_NON_PDF
        return RetrievalCategory.REVIEW_REQUIRED

    @staticmethod
    def _message_for(category: RetrievalCategory) -> str:
        messages = {
            RetrievalCategory.DIRECT_FILE_OK: "Direct PDF asset resolved.",
            RetrievalCategory.HARD_404: "Hard 404 response returned.",
            RetrievalCategory.SOFT_404: "Destination appears to be a soft 404 or not-found landing page.",
            RetrievalCategory.ALT_LANDING_PAGE_NON_PDF: "URL resolved to an HTML landing page instead of a PDF.",
            RetrievalCategory.REQUEST_ERROR: "Request failed before a valid response was returned.",
            RetrievalCategory.REVIEW_REQUIRED: (
                "Destination resolved to a non-PDF office file and should be handled by a "
                "format-specific review path."
            ),
        }
        return messages[category]
