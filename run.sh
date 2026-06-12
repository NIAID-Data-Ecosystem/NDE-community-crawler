#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$REPO_DIR/.logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/run-$(date +%Y-%m-%d).log"

echo "[$(date)] Starting NDE community crawler weekly run" | tee -a "$LOG_FILE"

cd "$REPO_DIR"

# Pull latest before running so memory files are up to date
git pull --ff-only 2>&1 | tee -a "$LOG_FILE"

# Run the agent
claude --print "$(cat prompts/weekly_run.md)" 2>&1 | tee -a "$LOG_FILE"

echo "[$(date)] Run complete" | tee -a "$LOG_FILE"
