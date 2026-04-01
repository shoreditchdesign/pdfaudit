from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from pypdf import PdfReader
from pypdf.constants import UserAccessPermissions
from pypdf.generic import ArrayObject, DictionaryObject


HEADING_TAGS = {"/H", "/H1", "/H2", "/H3", "/H4", "/H5", "/H6"}


@dataclass
class StructureElement:
    tag: str
    alt_text: str | None = None
    actual_text: str | None = None
    title: str | None = None
    raw: dict[str, Any] | None = None


def load_reader(pdf_path: Path) -> PdfReader:
    return PdfReader(str(pdf_path), strict=False)


def resolve_pdf_object(obj: Any) -> Any:
    current = obj
    seen: set[int] = set()
    while hasattr(current, "get_object"):
        identity = id(current)
        if identity in seen:
            break
        seen.add(identity)
        try:
            current = current.get_object()
        except Exception:
            break
    return current


def as_dict(obj: Any) -> DictionaryObject | None:
    resolved = resolve_pdf_object(obj)
    if isinstance(resolved, DictionaryObject):
        return resolved
    return None


def as_array(obj: Any) -> ArrayObject | None:
    resolved = resolve_pdf_object(obj)
    if isinstance(resolved, ArrayObject):
        return resolved
    return None


def as_text(value: Any) -> str:
    resolved = resolve_pdf_object(value)
    if resolved is None:
        return ""
    if isinstance(resolved, bytes):
        return resolved.decode("utf-8", errors="ignore").strip()
    return str(resolved).strip()


def get_catalog(reader: PdfReader) -> DictionaryObject:
    return resolve_pdf_object(reader.trailer["/Root"])


def get_viewer_preferences(reader: PdfReader) -> DictionaryObject | None:
    catalog = get_catalog(reader)
    return as_dict(catalog.get("/ViewerPreferences"))


def get_language(reader: PdfReader) -> str:
    catalog = get_catalog(reader)
    return as_text(catalog.get("/Lang"))


def get_metadata_title(reader: PdfReader) -> str:
    metadata = reader.metadata or {}
    title = getattr(metadata, "title", None)
    if title:
        return str(title).strip()
    return as_text(metadata.get("/Title")) if hasattr(metadata, "get") else ""


def display_doc_title_enabled(reader: PdfReader) -> bool:
    viewer_preferences = get_viewer_preferences(reader)
    if not viewer_preferences:
        return False
    return bool(resolve_pdf_object(viewer_preferences.get("/DisplayDocTitle")))


def has_page_labels(reader: PdfReader) -> bool:
    try:
        labels = reader.page_labels
    except Exception:
        labels = None
    return bool(labels)


def count_images_on_page(page: Any) -> int:
    resources = as_dict(page.get("/Resources"))
    if not resources:
        return 0
    xobjects = as_dict(resources.get("/XObject"))
    if not xobjects:
        return 0

    count = 0
    for obj in xobjects.values():
        obj_dict = as_dict(obj)
        if obj_dict and as_text(obj_dict.get("/Subtype")) == "/Image":
            count += 1
    return count


def analyze_text_content(reader: PdfReader) -> tuple[int, int, int]:
    total_text_chars = 0
    pages_with_text = 0
    pages_with_images = 0

    for page in reader.pages:
        text = ""
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        normalized = " ".join(text.split())
        if normalized:
            pages_with_text += 1
            total_text_chars += len(normalized)
        if count_images_on_page(page) > 0:
            pages_with_images += 1

    return total_text_chars, pages_with_text, pages_with_images


def is_probably_scanned(reader: PdfReader) -> tuple[bool, str]:
    total_text_chars, pages_with_text, pages_with_images = analyze_text_content(reader)
    total_pages = len(reader.pages)

    if total_pages == 0:
        return False, "PDF has no pages."
    if total_text_chars == 0 and pages_with_images > 0:
        return True, "No extractable text found and pages contain image XObjects."
    if pages_with_text == 0 and pages_with_images == total_pages:
        return True, "All pages appear image-based without extractable text."
    return False, f"Extractable text detected on {pages_with_text} of {total_pages} pages."


def get_outline_count(reader: PdfReader) -> int:
    try:
        outline = reader.outline
    except Exception:
        return 0

    def _count(nodes: Any) -> int:
        if isinstance(nodes, list):
            return sum(_count(node) for node in nodes)
        return 1

    return _count(outline)


def get_user_access_summary(reader: PdfReader) -> tuple[bool, str]:
    if not reader.is_encrypted:
        return True, "PDF is not encrypted."

    permissions = reader.user_access_permissions
    if permissions is None:
        return False, "PDF is encrypted and permissions could not be resolved."

    allowed = bool(
        permissions & UserAccessPermissions.EXTRACT
        or permissions & UserAccessPermissions.EXTRACT_TEXT_AND_GRAPHICS
    )
    if allowed:
        return True, "PDF is encrypted but text extraction permissions are enabled."
    return False, "PDF security settings block text extraction for assistive technology."


def get_structure_root(reader: PdfReader) -> DictionaryObject | None:
    catalog = get_catalog(reader)
    return as_dict(catalog.get("/StructTreeRoot"))


def _walk_structure_node(node: Any, sink: list[StructureElement]) -> None:
    resolved = resolve_pdf_object(node)

    if isinstance(resolved, ArrayObject):
        for item in resolved:
            _walk_structure_node(item, sink)
        return

    if not isinstance(resolved, DictionaryObject):
        return

    tag = as_text(resolved.get("/S"))
    if tag:
        sink.append(
            StructureElement(
                tag=tag,
                alt_text=as_text(resolved.get("/Alt")) or None,
                actual_text=as_text(resolved.get("/ActualText")) or None,
                title=as_text(resolved.get("/T")) or None,
                raw={key: as_text(value) for key, value in resolved.items() if key in {"/S", "/Alt", "/ActualText", "/T"}},
            )
        )

    kids = resolved.get("/K")
    if kids is not None:
        _walk_structure_node(kids, sink)


def get_structure_elements(reader: PdfReader) -> list[StructureElement]:
    struct_root = get_structure_root(reader)
    if not struct_root:
        return []
    elements: list[StructureElement] = []
    kids = struct_root.get("/K")
    if kids is not None:
        _walk_structure_node(kids, elements)
    return elements


def find_tags(elements: Iterable[StructureElement], *tags: str) -> list[StructureElement]:
    tag_set = set(tags)
    return [element for element in elements if element.tag in tag_set]


def get_heading_levels(elements: Iterable[StructureElement]) -> list[int]:
    levels: list[int] = []
    for element in elements:
        if element.tag not in HEADING_TAGS:
            continue
        if element.tag == "/H":
            levels.append(1)
            continue
        try:
            levels.append(int(element.tag[2:]))
        except ValueError:
            continue
    return levels


def get_form_field_objects(reader: PdfReader) -> list[DictionaryObject]:
    catalog = get_catalog(reader)
    acro_form = as_dict(catalog.get("/AcroForm"))
    if not acro_form:
        return []
    fields = as_array(acro_form.get("/Fields"))
    if not fields:
        return []
    field_objects: list[DictionaryObject] = []
    for field in fields:
        field_dict = as_dict(field)
        if field_dict:
            field_objects.append(field_dict)
    return field_objects


def get_form_tooltips(reader: PdfReader) -> list[str]:
    tooltips: list[str] = []
    for field in get_form_field_objects(reader):
        tooltip = as_text(field.get("/TU"))
        if tooltip:
            tooltips.append(tooltip)
    return tooltips


def get_page_tab_order_issues(reader: PdfReader) -> list[int]:
    issues: list[int] = []
    for index, page in enumerate(reader.pages, start=1):
        tabs = as_text(page.get("/Tabs"))
        if tabs and tabs != "/S":
            issues.append(index)
    return issues


def count_link_annotations(reader: PdfReader) -> int:
    total = 0
    for page in reader.pages:
        annots = as_array(page.get("/Annots"))
        if not annots:
            continue
        for annot in annots:
            annot_dict = as_dict(annot)
            if annot_dict and as_text(annot_dict.get("/Subtype")) == "/Link":
                total += 1
    return total
