from __future__ import annotations

from pathlib import Path

from pypdf import PdfWriter
from pypdf.constants import UserAccessPermissions
from pypdf.generic import BooleanObject, DictionaryObject, NameObject, TextStringObject

from app.models.domain import CheckStatus
from app.services.checks.rules import (
    rule_bookmarks,
    rule_language,
    rule_metadata,
    rule_security,
    rule_tagged_pdf,
)


def _write_pdf(path: Path, *, title: str | None = None, lang: str | None = None, display_doc_title: bool = False,
               add_bookmark: bool = False, encrypt_without_extract: bool = False, marked: bool = False) -> Path:
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    writer.add_blank_page(width=300, height=300)
    writer.add_blank_page(width=300, height=300)
    writer.add_blank_page(width=300, height=300)

    if title:
        writer.add_metadata({"/Title": title})

    if lang:
        writer.root_object[NameObject("/Lang")] = TextStringObject(lang)

    if display_doc_title:
        writer.root_object[NameObject("/ViewerPreferences")] = DictionaryObject(
            {NameObject("/DisplayDocTitle"): BooleanObject(True)}
        )

    if marked:
        writer.root_object[NameObject("/MarkInfo")] = DictionaryObject(
            {NameObject("/Marked"): BooleanObject(True)}
        )

    if add_bookmark:
        writer.add_outline_item("Start", 0)

    if encrypt_without_extract:
        permissions = UserAccessPermissions.PRINT
        writer.encrypt("user-password", permissions_flag=permissions)

    with path.open("wb") as handle:
        writer.write(handle)

    return path


def test_metadata_rule_passes_when_title_and_display_doc_title_present(tmp_path: Path) -> None:
    pdf_path = _write_pdf(
        tmp_path / "metadata-pass.pdf",
        title="Test PDF",
        display_doc_title=True,
    )
    result = rule_metadata.run(pdf_path)
    assert result.status == CheckStatus.PASS


def test_language_rule_fails_when_catalog_lang_missing(tmp_path: Path) -> None:
    pdf_path = _write_pdf(tmp_path / "language-fail.pdf", title="Test PDF", display_doc_title=True)
    result = rule_language.run(pdf_path)
    assert result.status == CheckStatus.FAIL


def test_bookmark_rule_fails_for_long_document_without_outline(tmp_path: Path) -> None:
    pdf_path = _write_pdf(tmp_path / "bookmark-fail.pdf", title="Test PDF", display_doc_title=True, lang="en-GB")
    result = rule_bookmarks.run(pdf_path)
    assert result.status == CheckStatus.FAIL


def test_security_rule_fails_when_extraction_permissions_are_blocked(tmp_path: Path) -> None:
    pdf_path = _write_pdf(
        tmp_path / "security-fail.pdf",
        title="Test PDF",
        display_doc_title=True,
        lang="en-GB",
        encrypt_without_extract=True,
    )
    result = rule_security.run(pdf_path)
    assert result.status == CheckStatus.FAIL


def test_tagged_pdf_rule_fails_when_structure_markers_are_missing(tmp_path: Path) -> None:
    pdf_path = _write_pdf(tmp_path / "tagged-fail.pdf", title="Test PDF", display_doc_title=True, lang="en-GB")
    result = rule_tagged_pdf.run(pdf_path)
    assert result.status == CheckStatus.FAIL


def test_tagged_pdf_rule_passes_when_mark_info_is_present(tmp_path: Path) -> None:
    pdf_path = _write_pdf(
        tmp_path / "tagged-pass.pdf",
        title="Test PDF",
        display_doc_title=True,
        lang="en-GB",
        marked=True,
    )
    result = rule_tagged_pdf.run(pdf_path)
    assert result.status == CheckStatus.PASS
