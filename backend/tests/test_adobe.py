from app.core.config import Settings
from app.models.domain import CheckStatus
from app.services.adobe import AdobeClient


def test_adobe_client_maps_report_findings_into_rule_results(monkeypatch) -> None:
    settings = Settings(
        ADOBE_CLIENT_ID="test-client",
        ADOBE_CLIENT_SECRET="test-secret",
    )
    client = AdobeClient(settings, enabled=True)

    sample_report = {
        "summary": {"status": "completed"},
        "categories": [
            {
                "title": "Visual Accessibility",
                "checks": [
                    {"title": "Color contrast", "status": "failed"},
                    {"title": "Reading order", "status": "needs manual check"},
                    {"title": "Document title", "status": "passed"},
                ],
            }
        ],
    }

    monkeypatch.setattr(client, "_run_accessibility_job", lambda _: sample_report)
    results = client.check_document("/tmp/example.pdf")

    assert results["colour_contrast_machine_check"].status == CheckStatus.NEEDS_MANUAL_REVIEW
    assert results["reading_order_machine_check"].status == CheckStatus.NEEDS_MANUAL_REVIEW
    assert results["adobe_full_check"].status == CheckStatus.NEEDS_MANUAL_REVIEW


def test_adobe_client_returns_api_unavailable_without_credentials() -> None:
    settings = Settings(
        ADOBE_CLIENT_ID="",
        ADOBE_CLIENT_SECRET="",
        ADOBE_SCOPE="",
    )
    client = AdobeClient(settings, enabled=True)
    results = client.check_document("/tmp/example.pdf")
    assert results["adobe_full_check"].status == CheckStatus.API_UNAVAILABLE
