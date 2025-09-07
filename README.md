# Daily SDE/Full‑Stack Job Digest (12:00 IST)

This automation searches Google Jobs (via SerpAPI) for entry-level SDE/full‑stack roles at MAANG + top startups, drafts a personalized LinkedIn DM for each role (OpenAI), and emails a clean HTML digest to your inbox.

## What you need
1. **SerpAPI key** (free tier works): https://serpapi.com/
2. **Gmail App Password** (NOT your normal password): https://myaccount.google.com/apppasswords
   - Enable 2‑Step Verification first, then generate an app password for "Mail".
3. *(Optional)* **OpenAI API key** for DM generation.
4. A place to run it daily:
   - **GitHub Actions** (recommended), or
   - Your own machine/server via cron.

## Quick Start (GitHub Actions)
1. Fork this repo or upload files to a new repo.
2. In the repo, go to **Settings → Secrets and variables → Actions → New repository secret** and add:
   - `SERPAPI_KEY`
   - `GMAIL_USER` (your full Gmail address)
   - `GMAIL_APP_PASSWORD` (the app password)
   - `TO_EMAIL` (where to send the digest)
   - *(optional)* `OPENAI_API_KEY`
   - *(optional)* `MAX_RESULTS`, `COMPANIES`, `ROLE_QUERY`, `SITES_HINT`
3. Commit.
4. The workflow runs **daily at 12:00 IST** (scheduled 06:30 UTC in Actions).

## Run locally
```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # fill in the values
python job_bot.py
```

## Tuning
- Edit `COMPANIES` to your target list.
- Change `ROLE_QUERY` to include "new grad", "fresher", "university grad".
- Increase `MAX_RESULTS` if needed.

## Notes
- LinkedIn scraping is intentionally avoided (fragile/TOS). Instead we search **official boards** via Google Jobs.
- OpenAI is optional; without it, the email still sends and you can write DMs manually.
- GitHub Actions uses UTC; 06:30 UTC = **12:00 IST**.
