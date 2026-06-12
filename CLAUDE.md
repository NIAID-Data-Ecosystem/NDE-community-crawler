# NDE Community Crawler

Agentic weekly crawler that discovers community forum posts relevant to the NIAID Data Ecosystem (data.niaid.nih.gov) and drafts replies for human review.

## What this project does

Each week, an agent crawls approved forums (Biostars, SEQanswers, Reddit r/bioinformatics, etc.) for posts where researchers are looking for infectious disease or immune-related datasets. Relevant posts become GitHub Issues with draft replies for a human to review and post manually.

## Key files

- `config/forums.json` — **human-editable** list of approved/pending/blocked forums
- `memory/seen_posts.json` — all posts ever examined, with relevance scores and status
- `memory/thread_registry.json` — threads being tracked for followup replies
- `memory/run_log.json` — weekly run history
- `prompts/weekly_run.md` — the full agent prompt executed each week
- `agent/fetch.py` — Cloudflare-aware page fetcher (Playwright + stealth) for forums behind a Cloudflare JS challenge (Biostars, SEQanswers)
- `scrapers/*.py` — per-forum scrapers for no-auth / credentialed APIs (Reddit OAuth, Bioconductor Discourse, legacy Biostars API-key fallback)
- `.env.example` / `docs/setup.md` — optional credentials (Reddit OAuth, etc.) and how to obtain them
- `setup.sh` / `requirements.txt` — one-time environment setup
- `run.sh` — cron entrypoint (git pull → `xvfb-run claude --print`)

## Two forum-access patterns

- **No-auth APIs** (Stack Exchange / Stack Overflow, Galaxy & Bioconductor Discourse) — plain `curl`, no credentials. Stack Exchange has been the most productive source.
- **Cloudflare-protected** (Biostars, SEQanswers) — go through `agent/fetch.py`, which clears the JS challenge with no API key. This supersedes the old "needs `BIOSTARS_API_KEY`" / "skip SEQanswers" approach; `scrapers/biostars.py` (curl_cffi + key) remains only as a fallback.

Optional credentials live in `.env` (copy from `.env.example`) — currently just Reddit OAuth for higher-fidelity Reddit access.

## Setup (one-time, per machine)

```bash
./setup.sh   # creates .venv, installs Playwright + Chromium, checks for xvfb
```

Needs `xvfb` (`sudo apt install xvfb`) because the fetcher runs a *headed* full
Chromium to clear Cloudflare — headless Chromium gets detected.

## Running manually

```bash
./run.sh
```

`run.sh` wraps the agent in `xvfb-run` and exports `$NDE_PYTHON` / `$NDE_FETCH`
so the prompt can call the fetcher.

## The Cloudflare fetcher

Biostars and SEQanswers sit behind a Cloudflare JS challenge that blocks
`curl`/`WebFetch` (403 "Just a moment..."). `agent/fetch.py` drives a real
browser to clear it:

```bash
xvfb-run -a .venv/bin/python agent/fetch.py "<url>" --text   # or --html
```

Exit codes: `0` ok, `2` Cloudflare escalated (back off / use search fallback),
`3` navigation error. Cloudflare escalates under bursts, so the prompt paces
requests (~7s apart) and falls back to `WebSearch site:<forum>` on exit 2.

## Managing forums

To add a forum manually, edit `config/forums.json` and add to `approved`:
```json
{
  "name": "Forum Name",
  "url": "https://...",
  "api": null,
  "notes": "Why this is relevant",
  "added_by": "human"
}
```

To block an agent-discovered forum, move it from `pending` to `blocked` and add a `reason` field.

## GitHub Issue labels

- `candidate-reply` — a post the agent found and drafted a reply for
- `forum-discovery` — a new community the agent suggests monitoring

## Environment

Requires `gh` CLI authenticated to the NIAID-Data-Ecosystem org.
