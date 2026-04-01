# V1 Parity Check

Date: 2026-04-01

This document captures the first bulk parity pass against the live HSBC audit tracker so the current state is easy to resume from.

## Scope

Control source:

- `docs/Audit tracker (Full. live).xlsx`

Control slice used:

- first `100` tracker rows with:
  - a linked source URL
  - existing audit/report status data

Artifacts generated during this pass:

- control slice:
  - `docs/artifacts/control_first_100.json`
- bulk audit workbook:
  - `docs/artifacts/audit-bf882cb2482e42c49e2a48441b4218bc.xlsx`
- parity comparison CSV:
  - `docs/artifacts/bulk_parity_first_100.csv`

## Run Notes

- Adobe auth and live PDF Services were enabled for this pass.
- The first bulk run failed at workbook generation because some PDF form tooltip strings contained illegal control characters for XLSX cells.
- Export sanitization was added in `backend/app/services/reporting.py`.
- The bulk run was rerun successfully after that fix.

## Top-Line Results

Across the first `100` control rows:

- `Axes Audit Status` parity: `89 / 100`
- `PDF/UA` parity: `58 / 97`
- `WCAG` parity: `43 / 97`

Interpretation:

- workflow/status parity is fairly strong
- PDF/UA parity is moderate
- WCAG parity is currently weak

## Retrieval Outcomes

Across the 100-row run:

- `88` `DIRECT_FILE_OK`
- `6` `SOFT_404`
- `5` `REVIEW_REQUIRED`
- `1` `REQUEST_ERROR`

This means some mismatches are due to live source-link behavior rather than checker logic.

## Main Mismatch Patterns

Most common control vs output bucket combinations:

1. `Control PDF/UA Pass, Our PDF/UA Pass, Control WCAG Pass, Our WCAG Fail`
   Count: `30`

2. `Control PDF/UA Fail, Our PDF/UA Fail, Control WCAG Fail, Our WCAG Fail`
   Count: `18`

3. `Control PDF/UA Pass, Our PDF/UA Fail, Control WCAG Pass, Our WCAG Fail`
   Count: `11`

4. `Control PDF/UA Pass, Our PDF/UA Pass, Control WCAG Fail, Our WCAG Fail`
   Count: `10`

5. `Control Partial, Our Fail, Control Partial, Our Fail`
   Count: `9`

Key implication:

- the biggest parity problem is over-failing WCAG where the control says `Pass`

## Current Read

### What is going well

- the app now performs real live audits against Adobe PDF Services
- export format is much closer to the tracker shape
- top-line status mapping is broadly usable
- the system is stable enough to process large batches

### What is not close enough yet

- WCAG rollup is too harsh
- some Python structural checks still over-fail compared with the control
- tracker-style notes are closer, but still not fully aligned to control phrasing

## Most Likely Root Causes

### 1. WCAG mapping is too strict

This is the biggest issue.

Current behavior likely over-penalizes:

- Adobe `Needs manual check`
- reading order concerns
- colour contrast manual-review signals
- some structural issues that the control does not appear to map directly to WCAG fail

### 2. Python rules are stricter than control logic

Examples seen earlier in the session:

- headings
- form tooltip policies
- some list/link/tagging checks

These may still be valid internal findings, but they should not always drive tracker-equivalent fail buckets.

### 3. Live-link instability affects parity

Some rows in the tracker now resolve to:

- soft 404s
- review-required non-PDF destinations
- request errors

Those rows cannot be treated as clean audit-parity comparisons.

## What Was Tuned During This Session

### PDF/UA rollup tuning

To better match the control workbook:

- `at_least_one_heading` was removed from the `PDF_UA_RULE_IDS` rollup

Why:

- it was over-failing `Business Price List`
- after that change, `Business Price List` matched the control top-line result:
  - `PDF/UA Pass`
  - `WCAG Fail`

## Recommended Next Steps

### Priority 1: Tune WCAG rollup

Focus first on the `30` rows where:

- control says `Pass / Pass`
- our output says `Pass / Fail`

Most likely actions:

- do not treat Adobe `Needs manual check` as automatic WCAG fail
- narrow which rule results actually contribute to tracker-style WCAG failure
- separate:
  - hard fail
  - manual-review signal
  - informational structural concern

### Priority 2: Review PDF/UA over-fails

Focus on rows where:

- control says `PDF/UA Pass`
- our output says `PDF/UA Fail`

This likely requires retuning which Python rules are:

- top-line blockers
- note-only findings
- manual-review-only findings

### Priority 3: Treat stale links separately

Rows with:

- `SOFT_404`
- `REVIEW_REQUIRED`
- `REQUEST_ERROR`

should be tracked separately from real audit-parity disagreements.

### Priority 4: Refine tracker-style notes

The export shape is now closer to the tracker, but next refinement should focus on:

- `PDF/UA Notes`
- `WCAG Notes`
- keeping them concise and closer to the control wording

## Suggested Next Analysis Pass

Use `docs/artifacts/bulk_parity_first_100.csv` and:

1. filter rows where:
   - `Control WCAG = Pass`
   - `Our WCAG = Fail`

2. group those rows by:
   - retrieval category
   - repeated failure summary patterns

3. adjust rollup rules before changing deeper parser logic

This should be the fastest route to improving parity.

## Bottom Line

V1 is now strong enough to run live, compare at scale, and produce meaningful parity data.

The main blocker to higher parity is not plumbing anymore.

It is rule severity and rollup calibration, especially for WCAG.

## Follow-Up Pass - Tagged PDF And WCAG Rollup

Date: `2026-04-01`

After the first parity pass, two additional rollup changes were made:

- `form_fields_have_tu` was removed from the `PDF_UA_RULE_IDS` rollup
- a Python `tagged_pdf_present` rule was added so untagged files can be blocked without relying only on Adobe wording

Artifacts from the follow-up Adobe-backed rerun:

- workbook:
  - `docs/artifacts/audit-parity-20260401104323.xlsx`
- parity CSV:
  - `docs/artifacts/bulk_parity_parity-20260401104323.csv`

Top-line results for this rerun:

- `Axes Audit Status` parity: `92 / 100`
- `PDF/UA` parity: `69 / 97`
- `WCAG` parity: `63 / 97`

What improved:

- `PDF/UA` parity moved from `58 / 97` to `69 / 97`
- `WCAG` parity moved from `43 / 97` to `63 / 97`
- `PDF/UA Pass -> Our PDF/UA Fail` direct-file mismatches dropped to `0`

What still stands out:

1. WCAG still has two competing mismatch families
   - `Control Pass -> Our Fail`: `10` direct-file rows
   - these are mostly files where Adobe exposes colour contrast as `NEEDS_MANUAL_REVIEW` and the tracker still says `Pass`
   - `Control Fail -> Our Pass`: `11` direct-file rows
   - these are mostly files where the tracker treats structural / readability / contrast findings as WCAG `Fail`, but our current rollup keeps them at `Pass`

2. Partial rows are still not tracker-aligned
   - `11` direct-file rows with `Partial` in the control still map to `Pass` or `Fail` in our output
   - the current export has no `Partial` bucket, so these rows can only approximate the tracker

3. Some remaining mismatches are due to live-link drift
   - retrieval distribution on this rerun:
     - `88` `DIRECT_FILE_OK`
     - `6` `SOFT_404`
     - `5` `REVIEW_REQUIRED`
     - `1` `REQUEST_ERROR`

Current read:

- the PDF/UA top-line rollup is much closer now
- the biggest remaining work is a better interpretation layer for Adobe-backed WCAG findings
- specifically:
  - which Adobe `FAIL` findings should really drive tracker-style WCAG fail
  - which Adobe `NEEDS_MANUAL_REVIEW` findings should stay note-only
