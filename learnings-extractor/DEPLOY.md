# learnings-extractor — deployment

Weekly offline pipeline that mines Claude Code session transcripts for recurring
failure modes and surfaces survivors as Vikunja approval cards. It **never**
writes a knowledge-base file; write-back is a separate human-run step
(`apply_candidates.py`) that opens a PR.

## Where it runs — CT 128 local cron (decided 2026-06-29)

The design (#1847) originally proposed a weekly bead on orchestrator **CT 157**,
but the transcripts to mine live in `/home/dev/.claude/projects` on **CT 128**
(`developmentenvironment`) — CT 157's `HOME=/opt/orchestrator` only holds its
own sparse dispatch-agent transcripts. So the extractor runs as a **local CT 128
user cron**, matching the validated pattern *"headless `claude -p` from a local
CT-128 cron is the right tool for scheduled homelab-touching agent work; the
wrapper owns observability."* (See operations #1864 for the rationale.)

## Canonical paths

| What | Path |
|---|---|
| Code (post-merge) | `/home/dev/workspace/learnings-extractor/` |
| Wrapper | `…/extract.sh` (stages 2–5, `timeout 1800` + Pushover) |
| State (high-water mark) | `~/.local/state/learnings-extractor/last_run.json` — **out of the repo** so weekly runs don't dirty the working tree |
| Review surface | Vikunja project **40 `learnings-review`** |
| Logs | `~/.local/state/learnings-extractor/extract.log` |

## Cron (installed on CT 128)

```cron
# learnings-extractor: weekly mine -> Vikunja learnings-review (project 40)
30 4 * * 0 PATH=/home/dev/.local/bin:/usr/local/bin:/usr/bin:/bin HOME=/home/dev [ -f /home/dev/workspace/learnings-extractor/extract.sh ] && /home/dev/workspace/learnings-extractor/extract.sh --project-id 40 --state /home/dev/.local/state/learnings-extractor/last_run.json >> /home/dev/.local/state/learnings-extractor/extract.log 2>&1
# learnings-extractor watchdog: alert if last run is stale (>8d)
0 9 * * 0 PATH=/home/dev/.local/bin:/usr/local/bin:/usr/bin:/bin HOME=/home/dev [ -f /home/dev/workspace/learnings-extractor/watchdog.sh ] && /home/dev/workspace/learnings-extractor/watchdog.sh /home/dev/.local/state/learnings-extractor/last_run.json >> /home/dev/.local/state/learnings-extractor/watchdog.log 2>&1
```

- **Sunday 04:30** extract (clear of the 02:00 cleanup jobs and 06:00 reports —
  staggered per the thundering-herd anti-pattern). Watchdog **Sunday 09:00**.
- The `[ -f … ]` guard makes the cron a **no-op until PR #57 merges** into the
  `/home/dev/workspace` main checkout, then it auto-activates — no post-merge
  step needed.
- No `--since`: the run reads the state high-water mark (first run cold-starts
  from mtime 0, capped at `MAX_WINDOWS=150`; subsequent runs are incremental).
- State advances **only on full success** (snapshot+rollback in `pipeline.py`),
  so a crash re-processes the same week rather than silently skipping it.

## Operate

```bash
# Dry-run (prints cards, creates nothing, touches no KB file). Use a throwaway
# --state so you don't burn the production high-water mark:
./extract.sh --dry-run --since 7d --state /tmp/le-dryrun.json

# Live (creates cards in Vikunja project 40):
./extract.sh --project-id 40 --state ~/.local/state/learnings-extractor/last_run.json

# Tunables (env): EXTRACT_MODEL (default claude-opus-4-8 — set EXTRACT_MODEL=
# claude-sonnet-4-6 to cut cost), EXTRACT_MAX_WINDOWS (default 150).
```

## Write-back (human-run, separate)

```bash
# 1. Review cards in Vikunja project 40; label an approved one 'approved'.
# 2. python3 -m learnings_extractor.apply_candidates --project-id 40        # dry-run
#    python3 -m learnings_extractor.apply_candidates --project-id 40 --apply # writes + opens PR
```

`apply_candidates.py` is the ONLY writer to KB files: full body → `<file>-archive.md`,
headline → the `@`-imported index (append-only, never overwrite), then a PR.

## Pushover

`extract.sh` alerts on every exit path (success/empty/fail/timeout) via the
shared homelab Pushover app (`infisical-get PUSHOVER_API_TOKEN` +
`PUSHOVER_USER_KEY`). Silent in `--dry-run` or if creds don't resolve.
`watchdog.sh` alerts if the high-water mark is older than `MAX_AGE_DAYS` (8).

## First live run

Validated 2026-06-29 via `--dry-run` against 7 days of real transcripts: 512
friction windows → 150 capped → Opus cluster → gemini cross-check → KB dedup →
3 cross-checked candidate cards in ~3:53, exit 0, no cards POSTed, no KB files
touched. Do one supervised live run before trusting the weekly cron.
