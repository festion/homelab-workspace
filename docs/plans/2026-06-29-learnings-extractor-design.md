# Learnings Extractor — Offline Self-Improvement Loop (Design)

**Date:** 2026-06-29
**Source task:** operations #1847
**Status:** Design approved, pending implementation

## Problem

Learnings/skills are captured manually in-session via the "3+ recurrence → propose a
skill" rule + end-of-session flush. This relies on a human/agent *noticing* recurrence
*within one session*. Cross-session patterns and skipped captures are lost.

## Solution

A weekly offline pipeline, dispatched as a bead on orchestrator CT 157, that mines recent
session transcripts for recurring failure modes, cross-checks each candidate with a second
model, and surfaces survivors as Vikunja approval cards. **No knowledge-base file is ever
written without explicit human approval of a card.**

## Decisions (brainstorming 2026-06-29)

| Decision | Choice |
|---|---|
| v1 scope | Full pipeline (not a narrow MVP) |
| Host / trigger | Weekly bead on orchestrator CT 157 |
| Surfacing | Vikunja approval cards in a `learnings-review` project |
| Extraction method | Deterministic signal pre-filter → LLM cluster |
| Stage-2 model | Opus (`claude-opus-4-8`), env-overridable; Sonnet is the cost lever |
| 2nd model | gemini-analyzer (cross-vendor agreement gate) |

## Pipeline (5 stages)

```
[1] Pre-filter (deterministic, Python)
    Scan ~/.claude/projects/*/*.jsonl modified in last 7d.
    Extract "friction windows" (N turns around a signal hit):
      - user corrections: \b(no|actually|wrong|don't|that's not)\b in USER turns only
      - tool_result errors
      - same-tool retries (≤3 turns apart)
      - git reverts/resets
      - "Request interrupted by user"
    Unconditional secret-redaction over every excerpt before it leaves this stage.
    Output: friction-windows.jsonl (excerpt + session id + project tag)

[2] Cluster + draft (claude -p, Opus)
    Reads ONLY the windows. Clusters by failure mode; keeps clusters with
    ≥2 occurrences across ≥2 sessions. Drafts each as a learning candidate
    (headline + one-line core + routing) OR a skill proposal (workflow recurs 3+×).
    Output: candidates.json (schema-validated)

[3] 2nd-model cross-check (gemini-analyzer, -o text, output-only/no file writes)
    Re-judge each: real pattern? correct routing? agree → auto-surface;
    disagree → conflict flag (the signal). garbage verdict → treated as conflict.

[4] Dedup vs existing KB (memory-search / ChromaDB)
    Drop near-duplicates of already-captured entries (cosine > threshold).

[5] Surface as Vikunja cards
    One card per surviving candidate in `learnings-review`: proposed entry +
    evidence excerpts + both model verdicts + routing target. Conflicts flagged
    in title. NOTHING written to KB files by the job.
```

**Write-back** is a separate, human-triggered step (`apply_candidates.py`): reads
*approved* cards, writes full body → `<file>-archive.md` + headline → the `@`-imported
index, then opens a **PR** (never a direct push, never an auto-write to an `@`-imported
file mid-session).

## Repo layout

```
learnings-extractor/
├── prefilter.py          # stage 1 — pure stdlib, deterministic, unit-tested
├── extract.sh            # stages 2-5 wrapper (timeout, logging, Pushover, watchdog)
├── prompts/
│   ├── cluster.md        # stage 2 prompt (clustering + draft rules)
│   └── crosscheck.md     # stage 3 gemini prompt (output-only)
├── apply_candidates.py   # write-back: approved cards → KB files → PR (human-run)
├── lib/
│   ├── signals.py        # friction-signal regexes + window extraction
│   ├── dedup.py          # memory-search wrapper (cosine threshold)
│   └── vikunja.py        # card create/read (reuse existing API helper)
├── state/last_run.json   # high-water mark (last processed mtime per project)
└── tests/                # pytest — synthetic jsonl fixtures
```

Default stage-2 model baked into `extract.sh` as `--model claude-opus-4-8` with an env
override.

## Error handling

- `timeout 1800` around everything; Pushover on every exit path + watchdog (validated
  headless-cron pattern).
- **Idempotency:** `last_run.json` advances only on full success → a crash re-processes
  the same week, never silently skips one. Re-runs are dedup-identical (stage 4 drops
  repeats), so a retry can't double-file cards.
- **LLM boundary:** stage-2 JSON and stage-3 verdicts schema-validated; one retry, then
  fail loud (no partial card creation). `JSONDecodeError` after a successful `claude -p`
  = failure, not empty.
- **Vikunja create is the last step** (only external mutation). A create whose
  response-parse fails may still have created the card — verify by query before re-filing.

## Self-improvement guardrails (from the task's sharpest critiques)

1. **Human-confirm is structural.** Terminal job state = "cards created." No KB write
   without an approved card.
2. **Echo-chamber defense.** The loop converges on consistency with past notes, not
   correctness. The gemini cross-check + conflict-flag exist so disagreement surfaces
   rather than being smoothed away. Conflicts are a feature.
3. **Never auto-write `@`-imported files** (prompt-cache breakage + echo amplification).
   `apply_candidates.py` writes archive body + index headline, opens a PR.
4. **No secrets transcript→card.** Unconditional redactor in stage 1.

## Testing

**Pre-filter (deterministic core, heaviest coverage):**
- Fixture per signal type → asserts exactly one window with the right turn span.
- Negatives: clean session = 0 windows; "no" in an *assistant* turn or code block does
  not trigger (user-role only).
- Boundaries: signal at file start/end clamps; overlapping signals merge to one window.
- Idempotency: second run with unchanged high-water mark = 0 new windows.
- Redaction: fake token in a pasted line is gone from the excerpt.

**LLM-boundary stages — contract tests, not output-quality:**
- `cluster.md` output schema-validated; malformed JSON → one retry → loud fail, no cards.
- `crosscheck.md` parse: agree/disagree/garbage → garbage = conflict (fail-safe toward
  surfacing), never silently agreement.
- `dedup.py`: identical-to-existing dropped; novel passes (tiny fixture KB, not live index).

**Integration:** `--dry-run` first (stage 5 prints instead of creating), eyeball
candidates, then one live run; confirm cards land with evidence + both verdicts.

**TDD order:** `signals.py` → `prefilter.py` (full unit suite green) → schema/parse
contracts → `dedup` → `vikunja`/`apply` last.
