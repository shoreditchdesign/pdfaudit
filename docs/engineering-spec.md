# HSBC PDF Audit Tool Engineering Spec

## Summary

This document defines the implementation plan for a batch-oriented PDF accessibility audit processor that:

- ingests sorted URL lists from the UI and source trackers
- downloads and validates the final asset destination
- evaluates deterministic HSBC accessibility rules in Python
- merges standardized accessibility signals from Adobe/Acrobat APIs
- emits tracker-friendly results with evidence, remediation notes, and manual-review flags

This product is not a PDF review workstation. It is a processor and reporting engine.

## Product Boundary

The system is responsible for:

- processing large URL batches
- identifying broken, soft-broken, or misdirected links
- running structural and metadata accessibility checks
- evaluating HSBC-specific policy rules
- merging Adobe accessibility output where available
- generating a single-run output workbook
- explaining why a check failed and how to remediate it

The system is not responsible for:

- building a tag-tree viewer or screen-reader preview
- replacing all semantic human review
- repairing PDFs
- rendering side-by-side manual inspection tools

## Architecture

### Ingestion Layer

- Accept URL batches from the UI and tracker-derived inputs
- Preserve source ordering and source row number
- Normalize URLs before processing
- Record original URL and final destination URL separately

### Retrieval Layer

- Resolve redirects
- Detect hard 404s
- Detect soft 404s and suspicious landing pages
- Classify response as PDF, approved non-PDF asset, or HTML landing page
- Store HTTP status, content type, redirect count, final URL, and page title/body signals

### Python Rule Engine

- Execute deterministic rules locally using Python libraries
- Emit normalized rule results
- Distinguish hard failures from manual-review boundaries
- Provide remediation text for every failing rule

### Adobe Integration Layer

- Submit PDFs to Adobe accessibility checking where configured
- Parse response into normalized rule results
- Keep raw Adobe payload available for debugging
- Do not let Adobe-specific outages block Python checks

### Aggregation Layer

- Merge URL checks, Python checks, and Adobe results into one audit record
- Derive overall status
- Build short summary notes and detailed failure evidence
- Preserve manual-review reasons distinctly from hard failures

### Output Layer

- Write a single-sheet workbook for the current run only
- Include source row number
- Include original and final URLs
- Include grouped accessibility result fields
- Include summary and debug columns

## Core Data Model

### Rule Definition

Each rule definition should include:

- `rule_id`
- `theme`
- `title`
- `execution_mode`
- `severity`
- `applies_when`
- `manual_review_capable`
- `default_remediation_template`

### Rule Result

Each rule result should include:

- `rule_id`
- `status`
- `confidence`
- `evidence`
- `remediation`
- `manual_review_reason`
- `source` (`python`, `adobe`, `heuristic`)
- `raw_payload_ref`

### Document Audit Record

Each processed document should store:

- `source_row_number`
- `pdf_name`
- `original_url`
- `final_url`
- `http_status`
- `content_type`
- `redirect_count`
- `retrieval_category`
- `page_count`
- `overall_status`
- `rule_results`
- `failure_summary`
- `failure_detail`
- `remediation_guidance`
- `manual_review_summary`

## Library And Service Choices

### Python Libraries

- `requests` or `httpx`
  URL resolution, redirects, final destination capture
- `pikepdf`
  metadata, catalog, permissions, bookmarks, page labels, tag access
- `pdfminer.six`
  text extraction, scanned-PDF heuristics
- `PyMuPDF`
  page count, text/image fallback extraction, page-level heuristics
- `openpyxl`
  workbook generation
- `rapidfuzz`
  optional heuristic matching between source name and landing page

### Adobe / Acrobat API

Use for:

- machine-verifiable PDF/UA checks
- colour contrast signals
- reading-order signals
- broad standardized accessibility categories

Do not use as the sole authority for HSBC-specific rules.

## Processing Pipeline

### Step 1. Source Capture

- Read URLs from UI submission or tracker-derived input
- Preserve document name and source row number when available
- Reject malformed entries early

### Step 2. Retrieval And Link Classification

- Resolve original URL
- capture final URL
- capture status code
- capture content type
- classify into:
  - `DIRECT_FILE_OK`
  - `HARD_404`
  - `SOFT_404`
  - `ALT_LANDING_PAGE_NON_PDF`
  - `REQUEST_ERROR`
  - `REVIEW_REQUIRED`

### Step 3. File Download

- Download only if final destination is a valid file candidate
- skip structural PDF checks on clear non-file destinations
- write temp files per job

### Step 4. Python Rule Execution

Run local deterministic checks first:

- metadata
- language
- security
- scanned-PDF detection
- bookmarks
- page labels
- headings
- alt-text presence and policy rules
- list/table/link structure
- form tooltip rules
- TOC threshold logic
- footnotes

### Step 5. Adobe Accessibility Checks

- Submit downloaded PDF where Adobe is enabled
- map Adobe results into normalized status values
- merge without overwriting Python-specific findings

### Step 6. Aggregation

- determine grouped result buckets:
  - retrieval
  - PDF/UA-style structural
  - WCAG-style machine-checkable
  - HSBC-specific policy
- derive overall status
- generate:
  - failure summary
  - failure detail
  - remediation guidance
  - manual review summary

### Step 7. Workbook Output

Generate a run-only workbook with no sample rows.

Recommended columns:

- `Row Number`
- `PDF Name`
- `Original URL`
- `Final URL`
- `HTTP Status`
- `Retrieval Category`
- `Page Count`
- `Overall Result`
- `PDF/UA Result`
- `WCAG Result`
- `HSBC Policy Result`
- `Metadata`
- `Language`
- `Security`
- `Scanned PDF`
- `Headings`
- `Alt Text`
- `Bookmarks`
- `TOC`
- `Lists`
- `Tables`
- `Links`
- `Forms`
- `Page Numbers`
- `Footnotes`
- `Colour Contrast (Adobe)`
- `Reading Order (Adobe)`
- `Failure Summary`
- `Failure Detail`
- `Remediation Guidance`
- `Manual Review Summary`

## Result Grouping Strategy

### Retrieval Group

- broken link
- soft 404
- suspicious redirect
- wrong landing page

### Structural Group

- metadata
- language
- title settings
- page labels
- bookmarks
- scanned-PDF detection

### Tagging Group

- headings
- alt text
- lists
- tables
- links
- forms
- footnotes
- TOC

### Adobe Group

- colour contrast
- reading order
- additional machine-verifiable accessibility checks

### HSBC Policy Group

- banned alt-text prefixes
- tooltip character limits
- tooltip uniqueness
- TOC thresholds
- custom wording or formatting rules

## Remediation Design

Every failing rule should emit remediation text from a stable template layer.

Examples:

- missing title:
  `Set a meaningful document title in metadata and enable DisplayDocTitle.`
- banned alt-text prefix:
  `Rewrite figure alt text to describe the content directly without starting with "Image of" or "Picture of".`
- bookmarks missing:
  `Add bookmarks aligned to major section headings because the document exceeds the bookmark threshold.`
- tooltip too long:
  `Shorten the form tooltip to the HSBC character limit while preserving clarity.`
- soft 404:
  `Replace the original URL with a valid direct asset link or confirm that the redirected landing page is the intended business destination.`

## Manual Review Policy

Manual review should be narrow and explicit.

Use `NEEDS_MANUAL_REVIEW` only for:

- alt-text meaning and quality
- true reading-order correctness
- ambiguous document-type classification for TOC logic
- questionable redirect intent
- malformed PDFs where structure cannot be parsed safely

Every manual-review result must include:

- why automation stopped
- what exactly the reviewer must confirm
- what likely fix is needed if the concern is confirmed

## Validation Strategy

### Benchmark Set

Create a benchmark set from already audited PDFs:

- pass/pass examples
- pass/fail examples
- fail/fail examples
- blocked or malformed examples
- redirect and link-edge cases

### Comparison Method

For each benchmark PDF:

- compare Python result vs tracker result
- compare Adobe result vs tracker result
- compare combined result vs tracker result
- record:
  - false positives
  - false negatives
  - manual-review deltas

### Quality Targets

- high precision on deterministic checks
- explicit manual-review flags instead of uncertain false passes
- no silent defaults to `NEEDS_MANUAL_REVIEW`
- high-quality remediation text for every deterministic failure

## Engineering Phases

### Phase 1. Retrieval And Link Audit

- robust URL resolver
- hard/soft 404 classifier
- final destination capture
- source row number propagation
- tracker comparison support

### Phase 2. Deterministic Structural Checks

- metadata
- language
- security
- scanned PDF
- bookmarks
- page labels

### Phase 3. Structural Tag Checks

- headings
- alt-text presence/prefix/length
- TOC logic
- lists
- tables
- links
- forms
- footnotes

### Phase 4. Adobe Integration

- API submission and retry handling
- normalized mapping to internal rule model
- degradation path when API unavailable

### Phase 5. Remediation And Reporting

- remediation templates
- workbook parity improvements
- grouped summary columns
- source row traceability

### Phase 6. Benchmark Validation

- compare against audited sample set
- tune heuristics
- reduce false positives
- document manual-review boundaries

## Recommended Immediate Work Order

1. finalize rule ids and normalized rule schema
2. improve link retrieval and destination classification
3. implement metadata/language/security/scanned/bookmark/page-label checks
4. implement heading/alt-text/forms checks
5. implement list/table/link/TOC/footnote checks
6. wire Adobe accessibility results
7. improve remediation guidance
8. tune workbook output to tracker expectations

## Definition Of Done

The processor is considered audit-ready for MVP when:

- it can run large URL batches reliably
- it classifies broken and soft-broken links accurately
- it performs deterministic HSBC structural checks locally
- it integrates Adobe checks without crashing on API absence
- it outputs evidence-rich fail/manual-review notes
- it produces a clean run-only workbook
- it is benchmarked against known audited examples with acceptable alignment
