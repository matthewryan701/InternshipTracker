# Internship Tracker

Checks the Trackr API every hour via GitHub Actions and emails you when new internship listings or events open up. Currently monitors UK Finance, UK Tech, and EU Finance across both internships and events.

---

## How it works

1. GitHub Actions runs `checker.py` every 4 hours
2. The script fetches all configured Trackr API endpoints and combines the results
3. A listing is considered "open" when its `openingDate` field is set
4. New open listings are compared against `seen_internships.json` to find ones not previously alerted
5. Any new listings trigger an HTML email showing the company, role, industry, and a link
6. `seen_internships.json` is committed back to the repo after each run, so state persists reliably across runs

---

## Sources currently monitored

| Region | Industry | Type |
|--------|----------|------|
| UK | Finance | Summer Internships (2027) |
| UK | Finance | Events (2027) |
| UK | Tech | Summer Internships (2026) |
| UK | Tech | Events (2026) |
| EU | Finance | Summer Internships (2026) |

To add more sources, simply add the relevant Trackr API URL to the `API_URLS` list at the top of `checker.py`. The pattern is:

```
https://api.the-trackr.com/programmes?region=UK&industry=Finance&season=2027&type=summer-internships
```

Parameters you can change: `region` (UK / EU), `industry` (Finance / Tech), `season`, `type` (summer-internships / events).

---

## Setup

### 1. Add GitHub Secrets

Go to your repo → **Settings → Secrets and variables → Actions → Secrets tab → New repository secret** and add:

| Secret name | Value |
|---|---|
| `EMAIL_SENDER` | The Gmail address sending the alerts |
| `EMAIL_PASSWORD` | A Gmail **App Password** (not your login password!) |
| `EMAIL_RECIPIENT` | The address that receives alerts |

**Getting a Gmail App Password:**
1. Enable 2-factor authentication at [myaccount.google.com/security](https://myaccount.google.com/security)
2. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Create a new app password (name it anything, e.g. "Internship Tracker")
4. Copy the 16-character code and paste it as `EMAIL_PASSWORD`

> Using a different email provider? Set `SMTP_HOST` and `SMTP_PORT` secrets too (defaults to Gmail on port 587).

---

### 2. Grant Actions write permission

So the workflow can commit `seen_internships.json` back to the repo:

1. Go to your repo → **Settings → Actions → General**
2. Scroll to **Workflow permissions**
3. Select **Read and write permissions**
4. Click **Save**

---

### 3. Push to GitHub

```bash
git init
git add .
git commit -m "Initial internship tracker"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

The workflow runs automatically every 4 hours. You can also trigger it manually from the **Actions** tab → **Run workflow**.

---

## File structure

```
.
├── checker.py                      # Main script — fetches APIs, detects new listings, sends email
├── requirements.txt                # Python dependencies (just requests)
├── seen_internships.json           # Auto-generated; tracks which listings have already been alerted
└── .github/
    └── workflows/
        └── update_run.yaml  # GitHub Actions schedule and steps
```

---

## Adding a new source

1. Find the Trackr API URL for the page you want to monitor (use browser DevTools → Network tab → filter XHR/Fetch)
2. Add the URL to the `API_URLS` list in `checker.py`
3. Commit and push — it will be included in the next run automatically

Non-Trackr sources (e.g. company career pages) can also be added, but may require custom fetch logic if the site uses JavaScript rendering or doesn't expose a JSON API.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `SMTPAuthenticationError` | Wrong email password | Use a Gmail App Password, not your login password |
| `403` error on git push | Actions lacks write permission | Enable read/write permissions in repo Settings → Actions |
| `No new listings found` but listings exist | Selectors or API URL wrong | Check the DEBUG output in the Actions log |
| Duplicate emails | `seen_internships.json` not persisting | Ensure read/write permissions are enabled so the commit step works |
