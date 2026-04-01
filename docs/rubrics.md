# HSBC PDF Audit Rubrics

This document defines the audit conditions the tool checks, how each condition is evaluated, and when a condition should be marked as `PASS`, `FAIL`, or `NEEDS_MANUAL_REVIEW`.

The intended execution model is:

- `Python deterministic`: fully machine-checkable using local PDF parsing and HTTP inspection
- `Adobe/Acrobat API`: machine-verifiable accessibility checks where Adobe adds meaningful signal
- `Python heuristic`: machine-assisted classification with bounded confidence
- `Manual-review required`: semantic or judgment-based review that should not be automated as a final authority

Each rule should emit:

- `rule_id`
- `theme`
- `execution_mode`
- `status`
- `evidence`
- `remediation`
- `confidence`
- `manual_review_reason` when applicable

## Status Definitions

- `PASS`: the rule was evaluated and met the expected condition
- `FAIL`: the rule was evaluated and did not meet the expected condition
- `NEEDS_MANUAL_REVIEW`: the rule could not be safely resolved without human judgment
- `API_UNAVAILABLE`: Adobe-dependent signal could not be obtained
- `N/A`: the rule does not apply to the document

## 1. URL And Retrieval

These rules validate that the source link is usable and that the tool is processing the expected asset.

### `URL_RESOLVES`

- Theme: `url_retrieval`
- Execution mode: `Python deterministic`
- Method: `requests` or `httpx` with redirect following
- Pass: URL resolves successfully within timeout
- Fail: DNS error, timeout, SSL failure, unreachable host, or hard 404
- Remediation: update the source URL or replace the missing asset

### `URL_IS_EXPECTED_FILE`

- Theme: `url_retrieval`
- Execution mode: `Python deterministic`
- Method: final URL, content type, and response headers
- Pass: final destination is a PDF or explicitly approved file type
- Fail: final destination is HTML when a PDF is expected
- Remediation: replace the source link with the direct asset URL

### `SOFT_404_REDIRECT`

- Theme: `url_retrieval`
- Execution mode: `Python heuristic`
- Method: inspect final destination URL, page title, and landing-page text
- Pass: final destination appears to be the intended file or a known acceptable landing page
- Fail: final destination is a recognized not-found page or equivalent broken-asset landing
- Manual review: only if a redirect could be intentional for business reasons
- Remediation: confirm intended redirect or replace with canonical asset URL

### `UNEXPECTED_LANDING_PAGE`

- Theme: `url_retrieval`
- Execution mode: `Python heuristic`
- Method: compare original file-like URL with final HTML destination and page title
- Pass: destination clearly matches intended business content
- Needs manual review: destination is a non-file landing page that may or may not be acceptable
- Remediation: confirm business intent or swap in the direct downloadable file

## 2. Document Identity And Metadata

These rules are deterministic and should be checked locally in Python.

### `DOC_TITLE_PRESENT`

- Theme: `metadata`
- Execution mode: `Python deterministic`
- Library: `pikepdf`
- Pass: document title metadata exists and is non-empty
- Fail: missing or empty title
- Remediation: set a meaningful document title in PDF metadata

### `DOC_AUTHOR_PRESENT`

- Theme: `metadata`
- Execution mode: `Python deterministic`
- Library: `pikepdf`
- Pass: author metadata exists and is non-empty
- Fail: missing or empty author
- Remediation: populate author metadata

### `DOC_DESCRIPTION_PRESENT`

- Theme: `metadata`
- Execution mode: `Python deterministic`
- Library: `pikepdf`
- Pass: description metadata exists and is non-empty
- Fail: missing or empty description
- Remediation: populate description metadata

### `DOC_KEYWORDS_PRESENT`

- Theme: `metadata`
- Execution mode: `Python deterministic`
- Library: `pikepdf`
- Pass: keywords metadata exists and is non-empty
- Fail: missing or empty keywords
- Remediation: populate keywords metadata

### `DISPLAY_DOC_TITLE_ENABLED`

- Theme: `metadata`
- Execution mode: `Python deterministic`
- Library: `pikepdf`
- Pass: `DisplayDocTitle = true`
- Fail: false or missing
- Remediation: enable document title display in viewer preferences

### `DOC_LANGUAGE_PRESENT`

- Theme: `metadata`
- Execution mode: `Python deterministic`
- Library: `pikepdf`
- Pass: `/Lang` exists and is a non-empty BCP-47 string
- Fail: missing or empty language
- Remediation: set the document language

### `PAGE_LABELS_PRESENT`

- Theme: `metadata`
- Execution mode: `Python deterministic`
- Library: `pikepdf`
- Pass: `/PageLabels` exists
- Fail: missing page labels
- Remediation: define page labels for the document

## 3. Security And Access

### `AT_ACCESS_NOT_BLOCKED`

- Theme: `security`
- Execution mode: `Python deterministic`
- Library: `pikepdf`
- Pass: accessibility extraction is not blocked by permissions
- Fail: assistive-technology access is blocked
- Remediation: adjust security permissions to allow accessibility extraction

## 4. Text Extraction And Scan Detection

### `EXTRACTABLE_TEXT_PRESENT`

- Theme: `scan_detection`
- Execution mode: `Python deterministic`
- Libraries: `pdfminer.six`, `PyMuPDF`
- Pass: text is extractable from content pages
- Fail: no extractable text on a page that contains visible content
- Remediation: OCR and retag the source document

### `LIKELY_SCANNED_PDF`

- Theme: `scan_detection`
- Execution mode: `Python heuristic`
- Libraries: `pdfminer.six`, `PyMuPDF`
- Pass: document behaves like a text-based PDF
- Fail: document appears image-based or scanned
- Remediation: OCR and rebuild tagging before downstream remediation

## 5. Tag Structure Presence

### `TAGGED_PDF_PRESENT`

- Theme: `structure`
- Execution mode: `Adobe/Acrobat API` or `Python deterministic`
- Pass: document is tagged
- Fail: no valid tag structure detected
- Remediation: create or repair the tag tree

### `TAG_TREE_READABLE`

- Theme: `structure`
- Execution mode: `Python deterministic`
- Library: `pikepdf`
- Pass: tag tree can be parsed reliably
- Needs manual review: malformed structure prevents reliable automated interpretation
- Remediation: inspect and repair tag structure in Acrobat

### `STRUCTURE_PARSE_ERROR`

- Theme: `structure`
- Execution mode: `Python deterministic`
- Library: `pikepdf`
- Pass: no parse error
- Needs manual review: malformed PDF structure prevents safe automated interpretation
- Remediation: validate and repair structure before re-auditing

## 6. Headings

### `AT_LEAST_ONE_HEADING`

- Theme: `headings`
- Execution mode: `Python deterministic`
- Library: `pikepdf`
- Pass: at least one heading tag exists
- Fail: no heading tags found
- Remediation: add semantic heading structure

### `SINGLE_H1_ONLY`

- Theme: `headings`
- Execution mode: `Python deterministic`
- Library: `pikepdf`
- Pass: exactly one `H1`
- Fail: zero or multiple `H1` tags
- Remediation: use a single top-level heading

### `NO_SKIPPED_HEADING_LEVELS`

- Theme: `headings`
- Execution mode: `Python deterministic`
- Library: `pikepdf`
- Pass: no heading-level jumps
- Fail: skipped levels detected
- Remediation: retag headings in hierarchical order

### `HEADINGS_USE_VALID_TAGS`

- Theme: `headings`
- Execution mode: `Python deterministic`
- Library: `pikepdf`
- Pass: heading content uses valid heading tags
- Fail: visually styled headings lack semantic tags
- Remediation: retag styled headings semantically

## 7. Alternative Text

### `FIGURE_ALT_PRESENT`

- Theme: `alt_text`
- Execution mode: `Python deterministic`
- Library: `pikepdf`
- Pass: non-decorative figures contain alt text
- Fail: figure tag missing `/Alt`
- Remediation: add descriptive alt text

### `ALT_TEXT_NOT_EMPTY`

- Theme: `alt_text`
- Execution mode: `Python deterministic`
- Library: `pikepdf`
- Pass: alt text is non-empty
- Fail: empty alt text
- Remediation: add meaningful alt text or mark decorative

### `ALT_TEXT_NOT_BANNED_PREFIX`

- Theme: `alt_text`
- Execution mode: `Python deterministic`
- Pass: alt text does not begin with banned prefixes such as `Image of` or `Picture of`
- Fail: banned prefix present
- Remediation: rewrite alt text without redundant lead-in phrases

### `ALT_TEXT_MAX_LENGTH`

- Theme: `alt_text`
- Execution mode: `Python deterministic`
- Pass: alt text is within configured HSBC character limit
- Fail: too long
- Remediation: shorten alt text to the essential meaning

### `DECORATIVE_IMAGES_NOT_UNTAGGED_FIGURES`

- Theme: `alt_text`
- Execution mode: `Python deterministic`
- Pass: decorative images are artifacts, not bare figure tags
- Fail: figure without alt text is not marked decorative
- Remediation: mark decorative graphics as artifacts or provide alt text

### `ALT_TEXT_QUALITY`

- Theme: `alt_text`
- Execution mode: `Manual-review required`
- Pass: alt text meaning is appropriate in context
- Needs manual review: semantic quality cannot be safely judged automatically
- Remediation: review whether alt text communicates purpose rather than appearance

## 8. Bookmarks And Navigation

### `BOOKMARKS_PRESENT_IF_GT_3_PAGES`

- Theme: `navigation`
- Execution mode: `Python deterministic`
- Library: `pikepdf`
- Pass: bookmarks exist when page count is greater than 3
- Fail: bookmarks missing on longer document
- Remediation: add bookmarks aligned to document sections

### `BOOKMARK_TREE_NOT_EMPTY`

- Theme: `navigation`
- Execution mode: `Python deterministic`
- Pass: bookmark structure contains entries
- Fail: bookmark tree exists but is empty
- Remediation: populate bookmark structure with navigable sections

## 9. Table Of Contents

### `TOC_PRESENT_GENERAL_DOC_IF_GE_5`

- Theme: `toc`
- Execution mode: `Python heuristic`
- Library: `pikepdf`
- Pass: TOC exists on general documents at or above threshold
- Fail: missing TOC where required
- Needs manual review: document type is ambiguous
- Remediation: add a semantic TOC or confirm document class

### `TOC_PRESENT_FORM_OR_FACTSHEET_IF_GE_21`

- Theme: `toc`
- Execution mode: `Python heuristic`
- Pass: TOC exists for long forms or factsheets
- Fail: missing TOC where required
- Needs manual review: filename/category heuristic uncertain
- Remediation: confirm document type and add TOC if applicable

### `TOC_CHILDREN_USE_TOCI`

- Theme: `toc`
- Execution mode: `Python deterministic`
- Pass: TOC items use proper child tags
- Fail: invalid TOC child structure
- Remediation: retag TOC items with correct TOC item tags

## 10. Lists

### `LISTS_USE_L`

- Theme: `lists`
- Execution mode: `Python deterministic`
- Pass: list containers use `<L>`
- Fail: visually presented lists are not semantically tagged
- Remediation: retag list structures properly

### `LIST_ITEMS_USE_LI`

- Theme: `lists`
- Execution mode: `Python deterministic`
- Pass: list items use `<LI>`
- Fail: missing or malformed list-item tags
- Remediation: wrap list entries in `<LI>`

### `LIST_ITEMS_HAVE_LBL_AND_LBODY`

- Theme: `lists`
- Execution mode: `Python deterministic`
- Pass: each list item contains label and body components
- Fail: label/body structure incomplete
- Remediation: add `<Lbl>` and `<LBody>` to list items

### `NESTED_LISTS_CORRECTLY_SCOPED`

- Theme: `lists`
- Execution mode: `Python deterministic`
- Pass: nested lists are correctly nested beneath `<LI>`
- Fail: invalid nesting
- Remediation: retag nested lists at the proper structural level

## 11. Tables

### `TABLES_USE_TABLE_TAG`

- Theme: `tables`
- Execution mode: `Python deterministic`
- Pass: tables use `<Table>`
- Fail: visual table lacks semantic table tag
- Remediation: retag as semantic table

### `TABLE_ROWS_USE_TR`

- Theme: `tables`
- Execution mode: `Python deterministic`
- Pass: rows use `<TR>`
- Fail: row structure invalid
- Remediation: rebuild table row tags

### `HEADERS_USE_TH`

- Theme: `tables`
- Execution mode: `Python deterministic`
- Pass: header cells use `<TH>`
- Fail: all cells use `<TD>`
- Remediation: tag header cells as `<TH>`

### `TABLE_CAPTION_PRESENT`

- Theme: `tables`
- Execution mode: `Python deterministic`
- Pass: caption exists when expected
- Fail: caption missing
- Remediation: add a meaningful table caption

### `CONSISTENT_CELL_COUNT`

- Theme: `tables`
- Execution mode: `Python deterministic`
- Pass: row structures are internally consistent
- Fail: inconsistent cell count without proper span attributes
- Remediation: normalize row/cell structure and spans

### `MERGED_CELLS_DEFINE_SPAN`

- Theme: `tables`
- Execution mode: `Python deterministic`
- Pass: merged cells declare proper spans
- Fail: span attributes missing
- Remediation: add `RowSpan` and `ColSpan`

### `EMPTY_CELLS_NOT_MISSING`

- Theme: `tables`
- Execution mode: `Python deterministic`
- Pass: intentionally empty cells are present as empty cells
- Fail: cells omitted structurally
- Remediation: preserve empty cells in semantic structure

## 12. Links

### `LINKS_USE_LINK_TAG`

- Theme: `links`
- Execution mode: `Python deterministic`
- Pass: links are semantically tagged
- Fail: interactive links lack semantic link tags
- Remediation: wrap interactive links in proper link tags

### `LINKS_INCLUDE_OBJR`

- Theme: `links`
- Execution mode: `Python deterministic`
- Pass: link object references are present
- Fail: missing object references
- Remediation: repair tagged link association

### `LINK_TEXT_PRESENT`

- Theme: `links`
- Execution mode: `Python deterministic`
- Pass: links contain visible/descriptive text
- Fail: no link text
- Remediation: add visible descriptive link text

## 13. Forms

### `FORM_FIELDS_HAVE_TU`

- Theme: `forms`
- Execution mode: `Python deterministic`
- Library: `pikepdf`
- Pass: each form field has a tooltip
- Fail: missing tooltip
- Remediation: add tooltip text to form field

### `TOOLTIP_MAX_LENGTH`

- Theme: `forms`
- Execution mode: `Python deterministic`
- Pass: tooltip length is within policy
- Fail: too long
- Remediation: shorten tooltip text

### `TOOLTIP_ALLOWED_CHARACTERS`

- Theme: `forms`
- Execution mode: `Python deterministic`
- Pass: tooltip only contains allowed characters
- Fail: disallowed characters present
- Remediation: normalize tooltip content

### `TOOLTIPS_UNIQUE`

- Theme: `forms`
- Execution mode: `Python deterministic`
- Pass: tooltips are unique
- Fail: duplicate tooltips detected
- Remediation: make field tooltips distinct

### `TAB_ORDER_IS_STRUCTURE`

- Theme: `forms`
- Execution mode: `Python deterministic`
- Pass: page tab order is set to structure
- Fail: tab order not structure-based
- Remediation: set page tab order to structure

### `TOOLTIP_WORDING_QUALITY`

- Theme: `forms`
- Execution mode: `Manual-review required`
- Needs manual review: wording clarity cannot be guaranteed automatically
- Remediation: confirm label language is understandable and unambiguous

## 14. Footnotes

### `FOOTNOTES_USE_NOTE`

- Theme: `footnotes`
- Execution mode: `Python deterministic`
- Pass: footnotes use `<Note>`
- Fail: footnotes are present but incorrectly tagged
- Remediation: retag footnotes as notes

### `FOOTNOTE_LABELS_USE_LBL`

- Theme: `footnotes`
- Execution mode: `Python deterministic`
- Pass: footnote labels use `<Lbl>`
- Fail: labels missing
- Remediation: add proper footnote labels

### `FOOTNOTE_NUMBERING_SEQUENTIAL`

- Theme: `footnotes`
- Execution mode: `Python deterministic`
- Pass: numbering is sequential
- Fail: numbering duplicates or skips
- Remediation: renumber footnotes sequentially

## 15. Contrast And Reading Order

### `COLOUR_CONTRAST_MACHINE_CHECK`

- Theme: `visual_accessibility`
- Execution mode: `Adobe/Acrobat API`
- Pass: Adobe machine check passes
- Fail: machine-detectable contrast failure
- Needs manual review: Adobe reports ambiguity or manual check requirement
- Remediation: fix source design contrast and regenerate PDF

### `READING_ORDER_MACHINE_CHECK`

- Theme: `visual_accessibility`
- Execution mode: `Adobe/Acrobat API`
- Pass: machine check passes
- Fail: machine-detectable ordering issue
- Needs manual review: Adobe reports manual check required
- Remediation: inspect and retag content order in Acrobat

### `READING_ORDER_TRUE_USER_SENSE`

- Theme: `visual_accessibility`
- Execution mode: `Manual-review required`
- Needs manual review: real narrative order still requires human validation
- Remediation: verify reading order with assistive-technology-aware review

## 16. Overall Audit Logic

The overall result should be derived using the following logic:

- `FAIL` if one or more deterministic or Adobe-backed rules fail
- `NEEDS_MANUAL_REVIEW` if no hard failures exist but one or more manual-only or uncertain rules remain unresolved
- `PASS` only if all applicable rules pass and no unresolved manual-review conditions remain
- `API_UNAVAILABLE` should only affect Adobe-backed subchecks and should not mask Python results

## 17. Output Expectations

For every failed or manual-review rule, the output should include:

- concise rule label
- evidence captured during processing
- remediation recommendation
- whether manual review is required
- why manual review is required when applicable

This rubric is intended to keep the processor strict, explainable, and aligned with HSBC-specific accessibility policy rather than defaulting broad classes of documents to `NEEDS_MANUAL_REVIEW`.
