#!/usr/bin/env bash
# Sibling watchdog: alert if the weekly run hasn't advanced state recently.
# Run from cron a few hours after the scheduled extract; Pushovers if the
# high-water mark in state/last_run.json is older than MAX_AGE_DAYS.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE="${1:-$SCRIPT_DIR/state/last_run.json}"
MAX_AGE_DAYS="${MAX_AGE_DAYS:-8}"

notify() {
  command -v pushover-send >/dev/null 2>&1 && pushover-send "$1" "$2" >/dev/null 2>&1 || true
}

if [ ! -f "$STATE" ]; then
  notify "learnings-extractor watchdog" "no state file at $STATE — run never succeeded?"
  exit 1
fi

hwm=$(python3 -c "import json,sys; print(json.load(open('$STATE')).get('hwm',0))")
now=$(date +%s)
age_days=$(python3 -c "print(($now-$hwm)/86400)")
if python3 -c "import sys; sys.exit(0 if $age_days > $MAX_AGE_DAYS else 1)"; then
  notify "learnings-extractor STALE" "last run ${age_days%.*}d ago (>${MAX_AGE_DAYS}d)"
  exit 1
fi
echo "ok: last run ${age_days%.*}d ago"
