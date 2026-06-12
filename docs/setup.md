# NDE Community Crawler — Setup Guide

## Prerequisites

- Python 3.9+
- GitHub CLI (`gh`) — for creating Issues automatically
- Git

## Installation

```bash
pip install praw python-dotenv curl-cffi playwright
python -m playwright install chromium
```

## Credentials

Copy `.env.example` to `.env` and fill in your credentials. The `.env` file
is gitignored and never committed.

```bash
cp .env.example .env
```

---

## Reddit

Reddit's API requires OAuth authentication even for read-only access.

1. Log in to Reddit and go to: https://www.reddit.com/prefs/apps
2. Click **"create another app..."** at the bottom
3. Fill in:
   - **Name:** NDE Community Crawler
   - **Type:** Select **script**
   - **Description:** Research bot monitoring dataset discovery questions
   - **redirect uri:** `http://localhost:8080`
4. Click **Create app**
5. Copy the values into `.env`:
   - `REDDIT_CLIENT_ID` = the short string under "personal use script"
   - `REDDIT_CLIENT_SECRET` = the "secret" value

Test:
```bash
python scrapers/reddit.py
```

---

## Biostars

Biostars is behind Cloudflare and requires an API key to access programmatically.

1. Create a Biostars account at https://www.biostars.org
2. Go to your profile → **API key** (or https://www.biostars.org/accounts/profile/)
3. Copy the key into `.env` as `BIOSTARS_API_KEY`

Test:
```bash
python scrapers/biostars.py
```

---

## GitHub CLI

The `gh` CLI is used to create GitHub Issues for candidate replies automatically.

**Install:**
```bash
winget install --id GitHub.cli   # Windows
brew install gh                  # macOS
```

**Authenticate:**
```bash
gh auth login
```

Select **GitHub.com** → **HTTPS** → **Login with a web browser** and follow the prompts.

Verify:
```bash
gh auth status
```

---

## Running manually

```bash
cd /path/to/NDE-community-crawler
claude --print "$(cat prompts/weekly_run.md)"
```

Or via the wrapper script (Linux/macOS):
```bash
bash run.sh
```

---

## Scheduling (weekly)

**Linux/macOS** — add to crontab (`crontab -e`):
```
0 8 * * 1 /bin/bash /path/to/NDE-community-crawler/run.sh
```

**Windows** — use Task Scheduler to run `run.sh` via Git Bash every Monday at 8am.
