# HSBC PDF Accessibility Audit Tool

Implementation-ready scaffold for a local PDF accessibility audit tool based on the HSBC PRD.

## Workspace

- `frontend/`: React 18 + Vite UI for URL input, progress, and results
- `backend/`: FastAPI API, in-memory jobs, audit pipeline, and XLSX report generation

## Quick Start

### One-time setup

```bash
cd /Users/austinshoreditch/Documents/Github/pdfaudit
npm run setup
```

### Launch both apps together

```bash
cd /Users/austinshoreditch/Documents/Github/pdfaudit
npm run dev
```

Frontend runs on `http://127.0.0.1:3001` and the backend runs on `http://127.0.0.1:8000`.

### Stop both apps

```bash
cd /Users/austinshoreditch/Documents/Github/pdfaudit
npm run stop
```

## Manual Start

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install '.[dev]'
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Environment

Copy `.env.example` to `.env` in the repo root or backend folder.

Optional files:

- `AUDIT_TEMPLATE_PATH`: path to the existing HSBC workbook template
- `AUDIT_SAMPLE_PDF_DIR`: path to local sample PDFs for development fixtures

Adobe setup:

- Add `ADOBE_CLIENT_ID` and `ADOBE_CLIENT_SECRET` to the root `.env`
- If your Adobe credential screen shows a scope value, also add `ADOBE_SCOPE`
- Leave `ADOBE_REGION=ue1` unless Adobe provisioned your PDF Services credentials in another region
- `ADOBE_BASE_URL` is optional and only needed if Adobe gives you a custom API hostname
- `ADOBE_POLL_INTERVAL_SECONDS` and `ADOBE_POLL_TIMEOUT_SECONDS` control job polling behavior

Once those values are set, the backend will automatically use Adobe checks when the UI toggle is enabled for a run.

## Testing

```bash
npm run test:frontend
npm run test:backend
```
