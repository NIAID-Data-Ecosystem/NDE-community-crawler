#!/usr/bin/env bash
# One-time environment setup for the NDE Community Crawler.
# Safe to re-run. Installs the Python env + browser, then checks the external
# prerequisites that cron can't (claude CLI, gh auth, xvfb) and fails loudly so
# a misconfigured server doesn't run quietly and produce nothing.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_DIR"

PROBLEMS=()   # hard failures: crawler cannot work until fixed
NOTES=()      # soft notes: optional / informational

# ── Python environment ────────────────────────────────────────────────────────
echo "==> Creating Python venv"
if ! command -v python3 >/dev/null 2>&1; then
  echo "FATAL: python3 not found. Install Python 3 + the venv module first."
  exit 1
fi
python3 -m venv .venv
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements.txt

echo "==> Installing Playwright Chromium + OS dependencies"
# 'install-deps' needs sudo; 'install chromium' fetches the browser build.
if ! .venv/bin/playwright install-deps chromium 2>/dev/null; then
  NOTES+=("Could not auto-install browser OS deps (needs sudo). If the browser fails to launch, run: sudo .venv/bin/playwright install-deps chromium")
fi
.venv/bin/playwright install chromium

# ── External prerequisites (cron can't set these up) ──────────────────────────
echo "==> Checking external prerequisites"

# xvfb — required: the fetcher runs a *headed* browser to clear Cloudflare.
if ! command -v xvfb-run >/dev/null 2>&1; then
  PROBLEMS+=("xvfb-run not found. Install with: sudo apt install xvfb")
fi

# claude CLI — required and must be authenticated (auth is interactive/per-machine).
if ! command -v claude >/dev/null 2>&1; then
  PROBLEMS+=("claude CLI not found on PATH. Install it and run 'claude' once to authenticate.")
else
  # A trivial prompt confirms auth works; unauthenticated claude errors/exits non-zero.
  if ! echo "ping" | claude --print >/dev/null 2>&1; then
    PROBLEMS+=("claude CLI is installed but not authenticated (a test prompt failed). Run 'claude' interactively to log in.")
  fi
fi

# gh CLI — required and must be authed to the org (used to create Issues).
if ! command -v gh >/dev/null 2>&1; then
  PROBLEMS+=("gh CLI not found. Install it, then run 'gh auth login' for the NIAID-Data-Ecosystem org.")
elif ! gh auth status >/dev/null 2>&1; then
  PROBLEMS+=("gh CLI is installed but not authenticated. Run 'gh auth login'.")
fi

# .env — optional (only Reddit OAuth lives here; everything else works without it).
if [ ! -f .env ]; then
  NOTES+=("No .env file. Optional — copy .env.example to .env only if you want Reddit OAuth.")
fi

# ── Report ────────────────────────────────────────────────────────────────────
echo ""
if [ ${#NOTES[@]} -gt 0 ]; then
  echo "Notes:"
  for n in "${NOTES[@]}"; do echo "  - $n"; done
  echo ""
fi

if [ ${#PROBLEMS[@]} -gt 0 ]; then
  echo "SETUP INCOMPLETE — fix these before scheduling the cron job:"
  for p in "${PROBLEMS[@]}"; do echo "  ✗ $p"; done
  exit 1
fi

echo "All prerequisites satisfied ✓"
echo ""
echo "Smoke-test the fetcher:"
echo "    xvfb-run -a .venv/bin/python agent/fetch.py 'https://seqanswers.com/' --text"
echo "Then do a full dry run:"
echo "    ./run.sh"
echo "Then add the weekly cron (8am Mon Pacific = 16:00 UTC):"
echo "    0 16 * * 1 PATH=/usr/local/bin:/usr/bin:/bin $REPO_DIR/run.sh"
