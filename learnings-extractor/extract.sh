#!/usr/bin/env bash
# learnings-extractor pipeline wrapper (stage-c discipline).
#
# Owns: timeout, logging, and Pushover on EVERY exit path. The pipeline logic
# (scan -> cluster -> cross-check -> dedup -> cards) lives in pipeline.py, which
# is responsible for the transactional state guard (advance high-water mark only
# on full success). Pass --dry-run to print cards instead of creating them.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

MODEL="${EXTRACT_MODEL:-claude-opus-4-8}"
export EXTRACT_MODEL="$MODEL"

DRY_RUN=0
for a in "$@"; do [ "$a" = "--dry-run" ] && DRY_RUN=1; done

# Pushover on every exit path; silent in dry-run or when no sender is available.
notify() {
  [ "$DRY_RUN" = 1 ] && return 0
  if command -v pushover-send >/dev/null 2>&1; then
    pushover-send "$1" "$2" >/dev/null 2>&1 || true
  fi
}

if timeout 1800 python3 -m learnings_extractor.pipeline "$@"; then
  notify "learnings-extractor" "weekly run completed"
  exit 0
else
  rc=$?
  if [ "$rc" = 124 ]; then
    notify "learnings-extractor TIMEOUT" "killed after 1800s"
  else
    notify "learnings-extractor FAILED" "exit $rc"
  fi
  exit "$rc"
fi
