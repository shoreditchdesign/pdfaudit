# Work Machine Handoff

This project state can be moved cleanly to another machine through the Git repo plus a few local-only files.

## What To Put In Git

Commit the project files that define the app and the audit logic:

- `backend/`
- `frontend/`
- `scripts/`
- `docs/`
- `README.md`
- `package.json`
- `package-lock.json`
- `.gitignore`
- `.env.example`

Do not commit:

- `.env`
- `backend/.env`
- `.venv/`
- `node_modules/`
- generated audit outputs in `Downloads/`

## Best Cross-Machine Workflow

1. Push the repo to your remote.
2. On the other machine, clone the repo.
3. Recreate your local env file from `.env.example`.
4. Re-enter Adobe credentials locally on that machine.
5. Run setup and start the app.

## Commands

On this machine:

```bash
cd /Users/austinshoreditch/Documents/Github/pdfaudit
git add .
git commit -m "Checkpoint Adobe-integrated PDF audit tool"
git push
```

On the other machine:

```bash
git clone <your-remote-url>
cd pdfaudit
cp .env.example .env
npm run setup
npm run dev
```

## Adobe Credentials

Add these locally to `.env` on the other machine:

```env
ADOBE_CLIENT_ID=...
ADOBE_CLIENT_SECRET=...
ADOBE_SCOPE=openid,AdobeID,DCAPI
ADOBE_REGION=ue1
```

If you also keep a `backend/.env`, make sure it does not contain blank Adobe values that override the root `.env`.

## How To Carry This Thread Forward

The safest practical method is to keep the repo as the source of truth and carry the important decisions in docs.

What to preserve:

- `docs/rubrics.md`
- `docs/engineering-spec.md`
- `docs/work-machine-handoff.md`
- any generated comparison workbooks or CSVs you still need

Recommended:

1. Commit the docs and code.
2. Copy any important generated audit outputs you want to keep into a tracked folder like `docs/artifacts/` before committing.
3. On the new machine, open the repo and use these docs as the context handoff.

## If You Want The Same Test Inputs

Keep a small tracked fixture list in the repo, for example:

- the 3 control URLs
- the control workbook path/name
- the latest generated comparison workbook name

That makes it easy to reproduce parity tests on another machine without relying on chat history.

## Important Note About The Chat Thread

The chat thread itself is not the reliable artifact to move between machines.

The reliable artifacts are:

- committed code
- committed docs
- optional committed test artifacts
- local `.env` recreated manually

If needed, copy key conclusions from the thread into docs rather than relying on the thread to be available on the second machine.
