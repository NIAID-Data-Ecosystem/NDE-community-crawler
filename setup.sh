#!/usr/bin/env bash
# One-time environment setup for the NDE Community Crawler.
# Safe to re-run. Requires: python3, and apt for xvfb + browser libs.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_DIR"

echo "==> Creating Python venv"
python3 -m venv .venv
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements.txt

echo "==> Installing Playwright Chromium + OS dependencies"
# 'install-deps' needs sudo; 'install chromium' fetches the browser build.
.venv/bin/playwright install-deps chromium || \
  echo "WARN: could not install OS deps automatically; you may need: sudo apt install xvfb libnss3 libatk1.0-0 libgbm1 ..."
.venv/bin/playwright install chromium

echo "==> Checking for xvfb (needed to run headed Chromium on a headless server)"
if ! command -v xvfb-run >/dev/null 2>&1; then
  echo "WARN: xvfb-run not found. Install with: sudo apt install xvfb"
fi

echo "==> Done. Test with:"
echo "    xvfb-run -a .venv/bin/python agent/fetch.py 'https://seqanswers.com/' --text"
