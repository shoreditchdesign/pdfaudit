from __future__ import annotations

from app.models.domain import ExecutionMode, RuleDefinition, RuleTheme


RULE_DEFINITIONS = {
    "url_resolves": RuleDefinition(
        rule_id="url_resolves",
        theme=RuleTheme.URL_RETRIEVAL,
        title="URL resolves",
        execution_mode=ExecutionMode.PYTHON_DETERMINISTIC,
        remediation_template="Update the source URL or replace the missing asset.",
    ),
    "url_is_expected_file": RuleDefinition(
        rule_id="url_is_expected_file",
        theme=RuleTheme.URL_RETRIEVAL,
        title="URL is expected file",
        execution_mode=ExecutionMode.PYTHON_DETERMINISTIC,
        remediation_template="Replace the source link with the direct downloadable asset URL.",
    ),
    "unexpected_landing_page": RuleDefinition(
        rule_id="unexpected_landing_page",
        theme=RuleTheme.URL_RETRIEVAL,
        title="Unexpected landing page",
        execution_mode=ExecutionMode.PYTHON_HEURISTIC,
        remediation_template="Confirm whether the landing page is intentional or replace it with the direct document URL.",
    ),
    "doc_title_present": RuleDefinition(
        rule_id="doc_title_present",
        theme=RuleTheme.METADATA,
        title="Document title present",
        execution_mode=ExecutionMode.PYTHON_DETERMINISTIC,
        remediation_template="Set a meaningful document title in metadata and enable DisplayDocTitle.",
    ),
    "doc_language_present": RuleDefinition(
        rule_id="doc_language_present",
        theme=RuleTheme.METADATA,
        title="Document language present",
        execution_mode=ExecutionMode.PYTHON_DETERMINISTIC,
        remediation_template="Set the document language in the PDF catalog.",
    ),
    "at_access_not_blocked": RuleDefinition(
        rule_id="at_access_not_blocked",
        theme=RuleTheme.SECURITY,
        title="Assistive technology access not blocked",
        execution_mode=ExecutionMode.PYTHON_DETERMINISTIC,
        remediation_template="Adjust security permissions so accessibility extraction is allowed.",
    ),
    "extractable_text_present": RuleDefinition(
        rule_id="extractable_text_present",
        theme=RuleTheme.SCAN_DETECTION,
        title="Extractable text present",
        execution_mode=ExecutionMode.PYTHON_HEURISTIC,
        remediation_template="OCR and retag the source document before re-auditing.",
    ),
    "tagged_pdf_present": RuleDefinition(
        rule_id="tagged_pdf_present",
        theme=RuleTheme.STRUCTURE,
        title="Tagged PDF present",
        execution_mode=ExecutionMode.PYTHON_DETERMINISTIC,
        remediation_template="Export or remediate the PDF with a valid structural tag layer before further testing.",
    ),
    "at_least_one_heading": RuleDefinition(
        rule_id="at_least_one_heading",
        theme=RuleTheme.HEADINGS,
        title="At least one heading present",
        execution_mode=ExecutionMode.PYTHON_DETERMINISTIC,
        remediation_template="Add semantic heading tags to the document structure.",
    ),
    "figure_alt_present": RuleDefinition(
        rule_id="figure_alt_present",
        theme=RuleTheme.ALT_TEXT,
        title="Figure alt text present",
        execution_mode=ExecutionMode.PYTHON_DETERMINISTIC,
        remediation_template="Add alt text to non-decorative figures or tag them as artifacts.",
    ),
    "bookmarks_present_if_gt_3_pages": RuleDefinition(
        rule_id="bookmarks_present_if_gt_3_pages",
        theme=RuleTheme.NAVIGATION,
        title="Bookmarks present when required",
        execution_mode=ExecutionMode.PYTHON_DETERMINISTIC,
        remediation_template="Add bookmarks aligned to major sections if the document exceeds the threshold.",
    ),
    "toc_present_general_doc_if_ge_5": RuleDefinition(
        rule_id="toc_present_general_doc_if_ge_5",
        theme=RuleTheme.TOC,
        title="TOC present for general documents",
        execution_mode=ExecutionMode.PYTHON_HEURISTIC,
        remediation_template="Add a semantic TOC or confirm the document classification.",
    ),
    "lists_use_l": RuleDefinition(
        rule_id="lists_use_l",
        theme=RuleTheme.LISTS,
        title="Lists use L tag",
        execution_mode=ExecutionMode.PYTHON_DETERMINISTIC,
        remediation_template="Retag list structures using semantic list tags.",
    ),
    "tables_use_table_tag": RuleDefinition(
        rule_id="tables_use_table_tag",
        theme=RuleTheme.TABLES,
        title="Tables use Table tag",
        execution_mode=ExecutionMode.PYTHON_DETERMINISTIC,
        remediation_template="Retag visual tables as semantic table structures.",
    ),
    "links_use_link_tag": RuleDefinition(
        rule_id="links_use_link_tag",
        theme=RuleTheme.LINKS,
        title="Links use Link tag",
        execution_mode=ExecutionMode.PYTHON_DETERMINISTIC,
        remediation_template="Wrap interactive links in proper link tags.",
    ),
    "form_fields_have_tu": RuleDefinition(
        rule_id="form_fields_have_tu",
        theme=RuleTheme.FORMS,
        title="Form fields have tooltips",
        execution_mode=ExecutionMode.PYTHON_DETERMINISTIC,
        remediation_template="Add unique tooltip text to each form field.",
    ),
    "footnotes_use_note": RuleDefinition(
        rule_id="footnotes_use_note",
        theme=RuleTheme.FOOTNOTES,
        title="Footnotes use Note tag",
        execution_mode=ExecutionMode.PYTHON_DETERMINISTIC,
        remediation_template="Retag footnotes using Note and Lbl structures.",
    ),
    "colour_contrast_machine_check": RuleDefinition(
        rule_id="colour_contrast_machine_check",
        theme=RuleTheme.VISUAL_ACCESSIBILITY,
        title="Colour contrast machine check",
        execution_mode=ExecutionMode.ADOBE_API,
        remediation_template="Adjust source design colours to meet contrast requirements and regenerate the PDF.",
    ),
    "reading_order_machine_check": RuleDefinition(
        rule_id="reading_order_machine_check",
        theme=RuleTheme.VISUAL_ACCESSIBILITY,
        title="Reading order machine check",
        execution_mode=ExecutionMode.ADOBE_API,
        remediation_template="Inspect and repair the reading order in Acrobat or the source file export.",
    ),
    "adobe_full_check": RuleDefinition(
        rule_id="adobe_full_check",
        theme=RuleTheme.VISUAL_ACCESSIBILITY,
        title="Adobe accessibility check",
        execution_mode=ExecutionMode.ADOBE_API,
        remediation_template="Review the Adobe accessibility report and address the flagged PDF/UA or WCAG issues.",
    ),
}

PDF_UA_RULE_IDS = {
    "tagged_pdf_present",
    "doc_title_present",
    "doc_language_present",
    "at_access_not_blocked",
    "figure_alt_present",
    "bookmarks_present_if_gt_3_pages",
    "lists_use_l",
    "tables_use_table_tag",
    "links_use_link_tag",
    "footnotes_use_note",
}

WCAG_RULE_IDS = {
    "url_resolves",
    "url_is_expected_file",
    "extractable_text_present",
    "colour_contrast_machine_check",
    "reading_order_machine_check",
}

HSBC_POLICY_RULE_IDS = {
    "unexpected_landing_page",
    "toc_present_general_doc_if_ge_5",
}
