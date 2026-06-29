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

# Pushover on every exit path; silent in dry-run or when creds don't resolve.
# Uses the shared homelab Pushover app (Infisical PUSHOVER_API_TOKEN +
# PUSHOVER_USER_KEY). infisical-get stderr is silenced (it echoes the value on
# stderr too) and the value is never printed.
notify() {
  [ "$DRY_RUN" = 1 ] && return 0
  local tok usr
  tok=$(infisical-get PUSHOVER_API_TOKEN 2>/dev/null) || return 0
  usr=$(infisical-get PUSHOVER_USER_KEY 2>/dev/null) || return 0
  [ -n "$tok" ] && [ -n "$usr" ] || return 0
  curl -s -o /dev/null --max-time 15 \
    --form-string "token=$tok" --form-string "user=$usr" \
    --form-string "title=$1" --form-string "message=$2" \
    https://api.pushover.net/1/messages.json || true
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
