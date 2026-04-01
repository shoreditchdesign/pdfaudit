# HSBC PDF Accessibility Audit Tool

Terminal-first PDF accessibility auditing for batch HSBC-style document reviews.

## What This Setup Does

This repo takes a plain-text list of document URLs, audits each document, and exports a multi-sheet Excel workbook plus a JSON summary.

At a high level, the current setup:

- checks whether each source URL resolves to a usable PDF
- runs machine-readable PDF/UA and semantic checks locally in Python
- runs Adobe Acrobat PDF Services checks when credentials are configured
- maps Adobe findings into clearer WCAG-oriented detail
- exports a workbook split into summary, WCAG, PDF/UA + semantics, remediation, and source retrieval sheets

The frontend is intentionally stripped back to a minimal scaffold for a future rebuild. The active workflow is the CLI.

## Repo Layout

- `backend/`: FastAPI app, audit engine, rules, reporting, tests
- `scripts/`: CLI entrypoints and helper scripts
- `target/`: input link lists
- `reports/`: generated Excel workbooks
- `summary/`: generated JSON summaries
- `frontend/`: placeholder scaffold only

## One-Time Setup

Run this from the repo root:

```bash
npm run setup
```

This will:

- create the backend virtualenv if needed
- install backend dependencies
- install root and frontend npm dependencies

## Running A Batch

### 1. Create an input file

Create a plain-text file in `target/` using this convention:

```text
target/audit-<theme>.txt
```

Examples:

- `target/audit-hsbc-april.txt`
- `target/audit-doctoral.txt`
- `target/audit-remediation-round-2.txt`

The file should contain one URL per line:

```text
https://www.example.com/file-1.pdf
https://www.example.com/file-2.pdf
```

Blank lines and `#` comments are ignored.

### 2. Run the audit

From the repo root:

```bash
npm run audit -- target/audit-hsbc-april.txt
```

If you want cleaner Adobe completion, use slower settings:

```bash
npm run audit -- target/audit-hsbc-april.txt --concurrency 1 --poll-timeout 180 --poll-interval 3
```

If you want to suppress npm’s extra wrapper lines in the terminal:

```bash
npm run --silent audit -- target/audit-hsbc-april.txt --concurrency 1 --poll-timeout 180 --poll-interval 3
```

You can also run the script directly:

```bash
./scripts/audit.sh target/audit-hsbc-april.txt --concurrency 1 --poll-timeout 180 --poll-interval 3
```

### 3. Read the outputs

The theme is derived from the input filename.

For `target/audit-hsbc-april.txt`, the outputs will be named like:

- `reports/audit-hsbc-april-<timestamp>.xlsx`
- `summary/audit-hsbc-april-<timestamp>.json`

## Output Structure

The Excel export is multi-sheet by default and currently includes:

- `Summary`
- `WCAG`
- `PDF UA + Semantics`
- `Remediation`
- `Source Retrieval`

This is designed so you can review high-level outcomes, specific WCAG/PDF/UA findings, remediation notes, and source-link issues separately.

## CLI Notes

The terminal runner is designed to be readable rather than noisy:

- one simple intro line
- one progress line per completed document
- a final summary block at the end

The runner also suppresses common low-value library noise such as repeated `pypdf` object-pointer warnings and OpenSSL environment warnings.

## Environment

Copy `.env.example` to `.env` in the repo root or backend folder.

Useful settings:

- `ADOBE_CLIENT_ID`
- `ADOBE_CLIENT_SECRET`
- `ADOBE_SCOPE`
- `ADOBE_REGION`
- `ADOBE_BASE_URL`
- `ADOBE_POLL_INTERVAL_SECONDS`
- `ADOBE_POLL_TIMEOUT_SECONDS`
- `AUDIT_TEMPLATE_PATH`
- `AUDIT_SAMPLE_PDF_DIR`

Adobe notes:

- keep `ADOBE_SCOPE=openid,AdobeID,DCAPI` unless Adobe tells you otherwise
- leave `ADOBE_REGION=ue1` unless your credentials were provisioned in another region
- Adobe checks are automatically used during CLI runs when valid credentials are present

## Development

### Backend only

```bash
npm run dev:backend
```

### Frontend scaffold only

```bash
npm run dev:frontend
```

The frontend is not the active product surface right now. It is only being kept as a rebuild scaffold.

### Stop running services

```bash
npm run stop
```

## Testing

Backend tests:

```bash
npm run test:backend
```

If you want to run pytest directly:

```bash
cd backend
PYTHONPATH=. backend/.venv/bin/python -m pytest tests
```
