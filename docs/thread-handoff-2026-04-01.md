# Thread Handoff - 2026-04-01

This file captures the important outcomes of the current Codex thread so work can continue on another machine without relying on chat history.

## Project Goal

Build a Python-first HSBC PDF accessibility audit tool that:

- processes batches of sorted PDF URLs
- classifies missing links and soft 404s
- runs deterministic PDF checks in Python
- uses Adobe PDF Services accessibility checking for machine-verifiable signals
- outputs a workbook that gets as close as possible to the existing HSBC control audit logic

The target is not an inspection UI like axes4. It is a batch processor with:

- `PASS`
- `FAIL`
- `NEEDS_MANUAL_REVIEW`

plus detailed remediation notes.

## What Has Been Implemented

### Backend foundation

- FastAPI backend scaffold is in place.
- Jobs now use normalized rule results and grouped bucket results.
- Report output is single-sheet and run-specific.
- Retrieval classification is implemented:
  - direct file OK
  - hard 404
  - soft 404
  - alt landing page / non-PDF
  - request error

### Python deterministic checks

Implemented with `pypdf`:

- metadata title / DisplayDocTitle
- document language
- security permissions for text extraction
- scanned / image-only detection
- bookmarks
- headings
- alt text presence and simple policy checks
- forms tooltip coverage
- links tagging presence
- lists structure basics
- tables structure basics
- TOC presence heuristic
- footnote tag presence

Shared parsing helpers live in:

- `backend/app/services/checks/pdf_utils.py`

### Adobe integration

Adobe auth and live PDF Services integration are working.

Implemented in:

- `backend/app/services/adobe.py`

Current Adobe flow:

1. fetch OAuth token
2. create asset
3. upload PDF
4. submit accessibility job
5. poll for completion
6. download JSON report
7. map findings into:
   - `colour_contrast_machine_check`
   - `reading_order_machine_check`
   - `adobe_full_check`

### Frontend

- React/Vite frontend is scaffolded and running
- shadcn-style primitives are in use
- Geist font applied
- overall UI was intentionally simplified

## Environment / Adobe Setup

Working root `.env` format:

```env
ADOBE_CLIENT_ID=...
ADOBE_CLIENT_SECRET=...
ADOBE_SCOPE=openid,AdobeID,DCAPI
ADOBE_REGION=ue1
```

Important discovery:

- `backend/.env` had blank Adobe values
- that was overriding the populated root `.env`
- config was updated so root `.env` now wins

Relevant config file:

- `backend/app/core/config.py`

## Control Files Used

Control workbook:

- `docs/Audit tracker (Full. live).xlsx`

Original older workbook template:

- `docs/Internal Only - Original 42  HSBC PDF for Audit.xlsx`

## 3-PDF Control Set Used In This Thread

### 1. Business Price List

URL:

- `https://www.business.hsbc.uk/-/media/media/uk/pdfs/regulations/business-price-list.pdf`

Control row:

- Axes Audit Status: `Complete`
- PDF/UA: `Pass`
- WCAG: `Fail`
- WCAG note: `There are 37 places in the document where the colour of the text isn't different enough from the colour behind it, making it harder to read.`

### 2. Managing Service Guide

URL:

- `https://www.business.hsbc.uk/-/media/media/uk/pdfs/campaigns/managing-service-guide.pdf`

Control row:

- Axes Audit Status: `Complete`
- PDF/UA: `Pass`
- WCAG: `Pass`

Important live finding:

- current live URL resolves to `https://www.business.hsbc.uk/notfound-404`
- this is a live-link issue, not necessarily an audit-parity issue

### 3. Presentation Export Doc Cover

URL:

- `https://www.business.hsbc.uk/-/media/media/uk/pdfs/solutions/presentation-export-doc-cover.pdf`

Control row:

- Axes Audit Status: `Blocked`
- PDF/UA: `Fail`
- WCAG: `Fail`
- PDF/UA note says the PDF lacks a structural tag layer for further testing

## Latest Live Comparison Outcome

Latest workbook from live app run:

- `/Users/austinshoreditch/Downloads/audit-5e26a3bb746a4e11a3ea2bbe664b6ffa.xlsx`

Parity status after tuning:

- `Business Price List`
  - Control: `PDF/UA Pass`, `WCAG Fail`
  - Current output: `PDF/UA Pass`, `WCAG Fail`
  - This is now aligned at the top-line bucket level

- `Managing Service Guide`
  - Control: `Pass / Pass`
  - Current output: soft 404 / not auditable live
  - unresolved due to stale or moved live link

- `Presentation Export Doc Cover`
  - Control: `Fail / Fail`
  - Current output: `Fail / Fail`
  - top-line bucket parity is aligned

Current parity summary:

- exact top-line match on live-auditable controls: `2/2`
- unresolved due to live link failure: `1/3`

## Important Tuning Done

To better match the control workbook:

- `at_least_one_heading` was removed from the `PDF_UA_RULE_IDS` rollup

Reason:

- it was over-failing `Business Price List`
- the control workbook still treated that file as `PDF/UA Pass`

This was a rollup-tuning change, not a removal of the heading check itself.

## Known Gaps

These still need work:

1. Tracker-style note mapping
   - current workbook outputs internal rule summaries
   - needs to map more closely to `PDF/UA Notes` and `WCAG Notes`

2. Managing Service Guide link issue
   - live URL currently soft-404s
   - need a valid source PDF before evaluating real parity

3. Adobe report mapping polish
   - now functional and live
   - still can be made more tracker-like in wording

4. Top-line overall result logic
   - currently still reflects all detected fails
   - may need a more control-like rollup for business-facing export

## Files Most Relevant To Continue From

Core backend:

- `backend/app/core/config.py`
- `backend/app/models/domain.py`
- `backend/app/services/jobs.py`
- `backend/app/services/reporting.py`
- `backend/app/services/retrieval.py`
- `backend/app/services/adobe.py`
- `backend/app/services/rule_catalog.py`

Python PDF checks:

- `backend/app/services/checks/pdf_utils.py`
- `backend/app/services/checks/rules/`

Tests:

- `backend/tests/test_api.py`
- `backend/tests/test_reporting.py`
- `backend/tests/test_rules.py`
- `backend/tests/test_adobe.py`

Docs:

- `docs/rubrics.md`
- `docs/engineering-spec.md`
- `docs/work-machine-handoff.md`
- `docs/thread-handoff-2026-04-01.md`

## Recommended Next Step

The next best move is:

1. use the control workbook fields as canonical export targets
2. map our findings into:
   - `Axes Audit Status`
   - `PDF/UA Results`
   - `WCAG Results`
   - `PDF/UA Notes`
   - `WCAG Notes`
3. reduce internal/noisy findings from top-line summaries when the control would still pass
4. find a valid live replacement for the Managing Service Guide PDF so parity can be tested fairly

## Current Run Commands

From repo root:

```bash
npm run setup
npm run dev
```

Backend tests:

```bash
./scripts/test-backend.sh
```

## Final Note

This file is the durable replacement for the chat thread.

If work resumes on another machine, start by reading:

1. `docs/thread-handoff-2026-04-01.md`
2. `docs/rubrics.md`
3. `docs/engineering-spec.md`
