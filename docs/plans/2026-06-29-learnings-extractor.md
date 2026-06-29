# Learnings Extractor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a weekly offline pipeline that mines Claude Code session transcripts for recurring failure modes, cross-checks each candidate against a second model, and surfaces survivors as Vikunja approval cards — never writing a knowledge-base file without explicit human approval.

**Architecture:** Five stages. (1) A deterministic Python pre-filter extracts "friction windows" from `~/.claude/projects/*/*.jsonl`. (2) `claude -p` (Opus) clusters windows and drafts candidates. (3) `gemini-analyzer` cross-checks each. (4) `memory-search` dedups against the existing KB. (5) Survivors become Vikunja cards. Write-back to KB files is a separate human-triggered step that opens a PR. Stages 1, 4, 5 and all parsing are deterministic Python (heavily tested); stages 2–3 are LLM calls behind schema-validated boundaries.

**Tech Stack:** Python 3.11 stdlib + pytest 8.4; `claude -p`; `gemini` CLI; `memory-search` CLI; Vikunja REST (creds from `~/.claude.json` → `mcpServers.vikunja.env`); bash wrapper (timeout/Pushover/watchdog) per the validated headless-cron pattern.

**Design reference:** `docs/plans/2026-06-29-learnings-extractor-design.md` (same worktree).

**Component root:** `learnings-extractor/` in the homelab-workspace repo.

---

## Dependency DAG (for parallel development)

```
Task 0 scaffold (ROOT — must land first)
   ├── Track A: Task 1 signals.py ──► Task 2 prefilter.py
   ├── Track B: Task 3 dedup.py
   ├── Track C: Task 4 vikunja.py ──► Task 7 apply_candidates.py
   └── Track D: Task 5 candidates.py (parse/validate) ──► Task 6 prompts
Task 8 extract.sh   (integration — needs 2,3,4,5,6)
Task 9 orchestrator bead   (needs 8)
```

Tracks A/B/C/D are independent after Task 0 and can be built in parallel (separate beads). Tasks 8–9 are the join points.

---

## Task 0: Project scaffold

**Files:**
- Create: `learnings-extractor/pyproject.toml`
- Create: `learnings-extractor/lib/__init__.py` (empty)
- Create: `learnings-extractor/tests/__init__.py` (empty)
- Create: `learnings-extractor/tests/conftest.py`
- Create: `learnings-extractor/state/.gitkeep`

**Step 1:** Write `pyproject.toml` — minimal, pytest config only:

```toml
[project]
name = "learnings-extractor"
version = "0.1.0"
requires-python = ">=3.11"

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"
```

**Step 2:** Write `tests/conftest.py` — a fixture that writes synthetic transcript `.jsonl` files (Claude Code transcript shape: one JSON object per line, each with `type` and `message`):

```python
import json
from pathlib import Path
import pytest

def _line(role, text, **extra):
    """One transcript line in Claude Code jsonl shape."""
    obj = {"type": role, "message": {"role": role, "content": text}}
    obj.update(extra)
    return json.dumps(obj)

@pytest.fixture
def transcript(tmp_path):
    """Write a transcript file from a list of (role, text) tuples; return its Path."""
    def _make(turns, name="session.jsonl"):
        p = tmp_path / name
        p.write_text("\n".join(_line(r, t) for r, t in turns) + "\n")
        return p
    return _make
```

**Step 3:** Verify pytest collects nothing yet:

Run: `cd learnings-extractor && python3 -m pytest`
Expected: `no tests ran` (exit 5) — confirms config is valid.

**Step 4: Commit**

```bash
git add learnings-extractor/
git commit -m "feat(learnings-extractor): project scaffold + pytest config + transcript fixture"
```

---

## Task 1: `lib/signals.py` — friction-signal detection + window extraction (Track A)

**Files:**
- Create: `learnings-extractor/lib/signals.py`
- Test: `learnings-extractor/tests/test_signals.py`

A "friction window" = the turns spanning `[hit_index - BEFORE, hit_index + AFTER]` around a signal hit. Signals:
- **correction** — `\b(no|actually|wrong|don't|that's not|not what)\b` in a **user** turn only.
- **tool_error** — a `tool_result` turn whose content marks an error.
- **retry** — same tool name invoked again within 3 turns.
- **revert** — a user/assistant turn containing `git revert`/`git reset --hard`/`git checkout --`.
- **interrupt** — `Request interrupted by user`.

**Step 1: Write failing tests**

```python
from learnings_extractor.lib import signals  # adjust import path per packaging

def turns(*pairs):
    return [{"role": r, "content": c, "type": r} for r, c in pairs]

def test_user_correction_detected():
    t = turns(("user","do X"),("assistant","done"),("user","no, that's wrong"))
    hits = signals.find_hits(t)
    assert any(h.kind == "correction" and h.index == 2 for h in hits)

def test_no_in_assistant_turn_not_detected():
    t = turns(("user","do X"),("assistant","no problem, done"))
    assert [h for h in signals.find_hits(t) if h.kind == "correction"] == []

def test_no_inside_codeblock_not_detected():
    t = turns(("user","```\nif no: pass\n```"))
    assert [h for h in signals.find_hits(t) if h.kind == "correction"] == []

def test_interrupt_detected():
    t = turns(("user","[Request interrupted by user]"))
    assert any(h.kind == "interrupt" for h in signals.find_hits(t))

def test_window_clamps_at_start_and_end():
    t = turns(("user","no, wrong"))
    w = signals.windows(t, before=2, after=2)
    assert w[0].start == 0 and w[0].end == 0

def test_overlapping_hits_merge_to_one_window():
    t = turns(("user","no"),("assistant","ok"),("user","wrong"))
    w = signals.windows(t, before=1, after=1)
    assert len(w) == 1  # the two correction hits merge
```

**Step 2:** Run: `python3 -m pytest tests/test_signals.py -v` → Expected: FAIL (module missing).

**Step 3: Implement `lib/signals.py`**

```python
import re
from dataclasses import dataclass

CORRECTION = re.compile(r"\b(no|actually|wrong|don't|that's not|not what)\b", re.I)
REVERT = re.compile(r"git (revert|reset --hard|checkout --)")
INTERRUPT = "Request interrupted by user"
_CODEBLOCK = re.compile(r"```.*?```", re.S)

@dataclass(frozen=True)
class Hit:
    index: int
    kind: str

@dataclass(frozen=True)
class Window:
    start: int
    end: int
    kinds: tuple

def _text(turn):
    c = turn.get("content", "")
    return c if isinstance(c, str) else str(c)

def _strip_code(s):
    return _CODEBLOCK.sub("", s)

def find_hits(turns):
    hits, recent_tools = [], {}
    for i, t in enumerate(turns):
        role, body = t.get("role"), _strip_code(_text(t))
        if role == "user" and CORRECTION.search(body):
            hits.append(Hit(i, "correction"))
        if INTERRUPT in body:
            hits.append(Hit(i, "interrupt"))
        if REVERT.search(body):
            hits.append(Hit(i, "revert"))
        if t.get("type") == "tool_result" and t.get("is_error"):
            hits.append(Hit(i, "tool_error"))
        tool = t.get("tool_name")
        if tool:
            if tool in recent_tools and i - recent_tools[tool] <= 3:
                hits.append(Hit(i, "retry"))
            recent_tools[tool] = i
    return hits

def windows(turns, before=3, after=3):
    hits = find_hits(turns)
    if not hits:
        return []
    spans = sorted((max(0, h.index - before),
                    min(len(turns) - 1, h.index + after), h.kind) for h in hits)
    merged = []
    for s, e, kind in spans:
        if merged and s <= merged[-1][1]:
            ps, pe, pk = merged[-1]
            merged[-1] = (ps, max(pe, e), pk | {kind})
        else:
            merged.append((s, e, {kind}))
    return [Window(s, e, tuple(sorted(k))) for s, e, k in merged]
```

**Step 4:** Run tests → Expected: PASS.

**Step 5: Commit** `feat(learnings-extractor): friction-signal detection + window merge`

---

## Task 2: `prefilter.py` — transcript scan, redaction, high-water mark (Track A)

**Files:**
- Create: `learnings-extractor/prefilter.py`
- Create: `learnings-extractor/lib/redact.py`
- Test: `learnings-extractor/tests/test_prefilter.py`, `tests/test_redact.py`

**Step 1: Redaction tests** (`tests/test_redact.py`):

```python
from learnings_extractor.lib.redact import redact

def test_token_redacted():
    assert "sk-" not in redact("key is sk-ant-abcd1234efgh5678ijkl")
def test_clean_text_unchanged():
    assert redact("nothing secret here") == "nothing secret here"
```

**Step 2:** Implement `lib/redact.py` — reuse the existing `redact` helper if importable, else a local regex set:

```python
import re
_PATTERNS = [
    re.compile(r"\b(sk-[a-zA-Z0-9_-]{8,})"),
    re.compile(r"\b(eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+)"),  # JWT
    re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{20,})"),
    re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[=:]\s*\S+"),
]
def redact(s):
    for p in _PATTERNS:
        s = p.sub("[REDACTED]", s)
    return s
```

**Step 3: Prefilter tests** (`tests/test_prefilter.py`) — use the `transcript` fixture:

```python
import json
from learnings_extractor import prefilter

def test_clean_session_yields_no_windows(transcript):
    p = transcript([("user","do X"),("assistant","done")])
    assert prefilter.process_file(p) == []

def test_friction_session_yields_window(transcript):
    p = transcript([("user","do X"),("assistant","done"),("user","no that's wrong")])
    out = prefilter.process_file(p)
    assert len(out) == 1 and "correction" in out[0]["kinds"]

def test_excerpt_is_redacted(transcript):
    p = transcript([("user","use sk-ant-secrettoken123456"),("user","no wrong")])
    out = prefilter.process_file(p)
    assert "sk-ant" not in json.dumps(out)

def test_high_water_mark_skips_unchanged(tmp_path, transcript):
    p = transcript([("user","no wrong")])
    state = tmp_path / "state.json"
    first = prefilter.scan([p.parent], state_path=state, since_mtime=0)
    second = prefilter.scan([p.parent], state_path=state, since_mtime=None)  # reads state
    assert first and second == []
```

**Step 4:** Run → FAIL.

**Step 5:** Implement `prefilter.py`:

```python
import json
from pathlib import Path
from learnings_extractor.lib import signals
from learnings_extractor.lib.redact import redact

def _load_turns(path):
    turns = []
    for line in Path(path).read_text().splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        msg = obj.get("message", {})
        turns.append({"role": msg.get("role", obj.get("type")),
                      "content": msg.get("content", ""),
                      "type": obj.get("type"),
                      "is_error": obj.get("is_error"),
                      "tool_name": obj.get("tool_name")})
    return turns

def process_file(path, before=3, after=3):
    turns = _load_turns(path)
    out = []
    for w in signals.windows(turns, before, after):
        excerpt = redact("\n".join(
            f"[{turns[i]['role']}] {turns[i]['content']}" for i in range(w.start, w.end + 1)))
        out.append({"session": Path(path).stem, "kinds": list(w.kinds), "excerpt": excerpt})
    return out

def scan(dirs, state_path, since_mtime=0):
    import os, time
    if since_mtime is None:
        since_mtime = json.loads(Path(state_path).read_text()).get("hwm", 0) if Path(state_path).exists() else 0
    results, max_mtime = [], since_mtime
    for d in dirs:
        for f in Path(d).glob("*.jsonl"):
            m = f.stat().st_mtime
            if m <= since_mtime:
                continue
            results.extend(process_file(f))
            max_mtime = max(max_mtime, m)
    # advance high-water mark ONLY here (caller commits success separately)
    Path(state_path).write_text(json.dumps({"hwm": max_mtime}))
    return results
```

> **Note:** `scan` advances the high-water mark on return. Per the design, `extract.sh` must only call `scan` once per run and treat a downstream failure as "re-process next week" by NOT persisting state until full success. For the unit test the simple write is fine; the wrapper handles the transactional guard (Task 8).

**Step 6:** Run → PASS. **Commit** `feat(learnings-extractor): prefilter scan + redaction + high-water mark`

---

## Task 3: `lib/dedup.py` — memory-search dedup wrapper (Track B)

**Files:** Create `learnings-extractor/lib/dedup.py`; Test `tests/test_dedup.py`.

**Step 1: Test** (inject a fake search function — no live index in tests):

```python
from learnings_extractor.lib import dedup

def fake_search(query, k):
    return [{"score": 0.95, "path": "x"}] if "stale DNS" in query else []

def test_duplicate_dropped():
    cands = [{"headline":"stale DNS thing","core":"..."}]
    assert dedup.filter_new(cands, search=fake_search, threshold=0.85) == []

def test_novel_kept():
    cands = [{"headline":"brand new pattern","core":"..."}]
    assert len(dedup.filter_new(cands, search=fake_search, threshold=0.85)) == 1
```

**Step 2:** FAIL. **Step 3: Implement:**

```python
import json, subprocess

def _cli_search(query, k):
    out = subprocess.run(["memory-search", query, "--json", "--k", str(k)],
                         capture_output=True, text=True, timeout=60)
    return json.loads(out.stdout) if out.stdout.strip() else []

def filter_new(candidates, search=_cli_search, threshold=0.85, k=3):
    kept = []
    for c in candidates:
        hits = search(f"{c['headline']} {c.get('core','')}", k)
        if not any(h.get("score", 0) >= threshold for h in hits):
            kept.append(c)
    return kept
```

**Step 4:** PASS. **Commit** `feat(learnings-extractor): KB dedup via memory-search`

> Verify the real `memory-search --json --k` flags before wiring live; adjust `_cli_search` to the actual CLI contract if it differs.

---

## Task 4: `lib/vikunja.py` — approval-card create/read (Track C)

**Files:** Create `learnings-extractor/lib/vikunja.py`; Test `tests/test_vikunja.py`.

Creds: read `VIKUNJA_URL` + `VIKUNJA_API_TOKEN` from `~/.claude.json` → `mcpServers.vikunja.env` (same source `vikunja-queue` uses). All HTTP via stdlib `urllib` (no new deps).

**Step 1: Test** (mock the HTTP layer):

```python
from learnings_extractor.lib import vikunja

def test_card_body_includes_evidence_and_verdicts():
    body = vikunja.render_card({
        "kind":"learning","headline":"H","core":"C","routing":"global",
        "evidence":["s1","s2"], "primary":"draft", "crosscheck":{"verdict":"agree"}})
    assert "H" in body and "agree" in body and "s1" in body

def test_conflict_flagged_in_title():
    t = vikunja.card_title({"headline":"H","crosscheck":{"verdict":"disagree"}})
    assert t.startswith("[CONFLICT]")
```

**Step 2:** FAIL. **Step 3: Implement** `render_card`, `card_title`, and a `create_card(project_id, candidate)` that POSTs to `/api/v1/projects/{id}/tasks` with the bearer token; `load_creds()` parses `~/.claude.json`. Keep `create_card` thin (the tested logic is `render_card`/`card_title`).

**Step 4:** PASS (logic tests; the live POST is exercised in Task 8 integration `--dry-run`). **Commit** `feat(learnings-extractor): vikunja approval-card rendering + create`

---

## Task 5: `lib/candidates.py` — stage-2/3 schema validation + verdict parse (Track D)

**Files:** Create `learnings-extractor/lib/candidates.py`; Test `tests/test_candidates.py`.

**Step 1: Tests:**

```python
import pytest
from learnings_extractor.lib import candidates

VALID = '[{"kind":"learning","headline":"H","core":"C","routing":"global","evidence_session_ids":["s1"],"occurrence_count":2}]'

def test_valid_parses():
    assert len(candidates.parse_candidates(VALID)) == 1

def test_malformed_raises():
    with pytest.raises(candidates.SchemaError):
        candidates.parse_candidates("not json")

def test_missing_field_raises():
    with pytest.raises(candidates.SchemaError):
        candidates.parse_candidates('[{"kind":"learning"}]')

def test_garbage_verdict_is_conflict():
    assert candidates.parse_verdict("???")["verdict"] == "disagree"  # fail-safe toward surfacing

def test_agree_verdict():
    assert candidates.parse_verdict('{"verdict":"agree","reason":"r"}')["verdict"] == "agree"
```

**Step 2:** FAIL. **Step 3: Implement** with stdlib only (hand-rolled validation, no jsonschema dep):

```python
import json

class SchemaError(Exception): pass
REQUIRED = {"kind","headline","core","routing","evidence_session_ids","occurrence_count"}

def parse_candidates(text):
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise SchemaError(f"bad json: {e}")
    if not isinstance(data, list):
        raise SchemaError("expected a list")
    for c in data:
        missing = REQUIRED - set(c)
        if missing:
            raise SchemaError(f"missing fields: {missing}")
    return data

def parse_verdict(text):
    try:
        obj = json.loads(text)
        v = obj.get("verdict")
        if v not in ("agree","disagree"):
            return {"verdict":"disagree","reason":"unparseable verdict"}
        return {"verdict": v, "reason": obj.get("reason","")}
    except json.JSONDecodeError:
        return {"verdict":"disagree","reason":"unparseable verdict"}
```

**Step 4:** PASS. **Commit** `feat(learnings-extractor): candidate schema validation + fail-safe verdict parse`

---

## Task 6: Prompt files (Track D)

**Files:** Create `learnings-extractor/prompts/cluster.md`, `prompts/crosscheck.md`; Test `tests/test_prompts.py`.

**Step 1: Contract test** — the prompts must demand strict JSON and (for gemini) output-only:

```python
from pathlib import Path
P = Path(__file__).parent.parent / "prompts"

def test_cluster_prompt_demands_json_array():
    t = (P/"cluster.md").read_text()
    assert "JSON" in t and "occurrence_count" in t and "≥2" in t

def test_crosscheck_prompt_is_output_only():
    t = (P/"crosscheck.md").read_text()
    assert "do not write" in t.lower() and "output only" in t.lower()
```

**Step 2:** FAIL. **Step 3:** Write the two prompts.
- `cluster.md`: role, input shape (friction windows JSON), clustering rule (≥2 occurrences across ≥2 sessions), routing rules (global toolchain → `~/.claude/learnings/`; homelab/project-specific → project `.claude/learnings/`; workflow recurring 3+× → skill proposal), and a **strict** output spec = a JSON array matching `lib/candidates.REQUIRED`, no prose.
- `crosscheck.md`: gemini, `-o text`, explicit "do not use any tools, do not write any files, output ONLY a JSON object `{verdict, reason}`" (per the gemini-CLI learning).

**Step 4:** PASS. **Commit** `feat(learnings-extractor): cluster + crosscheck prompts`

---

## Task 7: `apply_candidates.py` — write-back (human-run) (Track C, after Task 4)

**Files:** Create `learnings-extractor/apply_candidates.py`; Test `tests/test_apply.py`.

The ONLY writer to KB files. Reads cards labeled `approved`; for each, writes the **full body** to `<file>-archive.md` and a **headline line** to the `@`-imported index, then opens a **PR** (never direct push, never mid-session auto-write of an `@`-imported file).

**Step 1: Tests** (filesystem-level, against tmp fixture KB):

```python
from learnings_extractor import apply_candidates as ap

def test_writes_archive_body_and_index_headline(tmp_path):
    idx = tmp_path/"anti-patterns.md"; arc = tmp_path/"anti-patterns-archive.md"
    idx.write_text("# Index\n"); arc.write_text("# Archive\n")
    ap.write_entry(idx, arc, headline="### New rule — 2026-06-29", body="full body text")
    assert "### New rule" in idx.read_text()
    assert "full body text" in arc.read_text()
    assert "full body text" not in idx.read_text()  # body NEVER in @-imported index

def test_headline_byte_identical_between_files(tmp_path):
    idx = tmp_path/"i.md"; arc = tmp_path/"a.md"; idx.write_text(""); arc.write_text("")
    h = "### Title — 2026-06-29"
    ap.write_entry(idx, arc, headline=h, body="x")
    assert h in idx.read_text() and h in arc.read_text()  # anchor for grep/memory-search
```

**Step 2:** FAIL. **Step 3:** Implement `write_entry` (append-style `Edit`-equivalent, never overwrite — mirrors the "never Write a learnings file" mistake) + a `main()` that lists approved cards via `lib/vikunja`, calls `write_entry`, and shells `git checkout -b` + `gh pr create`. Gate `main()` behind an explicit `--apply` flag; default is dry-run print.

**Step 4:** PASS. **Commit** `feat(learnings-extractor): write-back applies approved cards via PR`

---

## Task 8: `extract.sh` — pipeline wrapper (integration; needs 2,3,4,5,6)

**Files:** Create `learnings-extractor/extract.sh`; Test `tests/test_extract_dryrun.py` (smoke).

**Step 1:** Write `extract.sh` (stage-c discipline):
- `set -euo pipefail`; `timeout 1800` around the python orchestration.
- Default `MODEL="${EXTRACT_MODEL:-claude-opus-4-8}"`.
- Pipeline: `prefilter.scan` → if zero windows, Pushover "no friction this week" + exit 0 (do NOT advance state on empty? — empty IS success, advance). → `claude -p --model "$MODEL" < prompts/cluster.md + windows` → `candidates.parse_candidates` (retry once on `SchemaError`, then fail loud) → per-candidate `gemini ... < prompts/crosscheck.md` → `candidates.parse_verdict` → `dedup.filter_new` → `vikunja.create_card`.
- **Transactional state:** persist the high-water mark ONLY after `vikunja.create_card` for all survivors succeeds.
- Pushover on every exit path (success/empty/fail/timeout) + a `watchdog.sh` sibling. Reuse `~/stage-c-1545/` as the template.
- `--dry-run`: stage 5 prints cards instead of POSTing.

**Step 2: Smoke test** — run `bash extract.sh --dry-run --since 7d` against a temp transcript dir with one planted friction window; assert exit 0 and a card JSON printed. (Mock `claude`/`gemini` with stub scripts on PATH that echo canned JSON, so the test is hermetic.)

**Step 3:** Iterate to green. **Commit** `feat(learnings-extractor): pipeline wrapper with transactional state + dry-run`

---

## Task 9: Orchestrator CT 157 weekly bead (needs 8)

**Files:** Create `learnings-extractor/bead.md` (or the orchestrator's bead-definition format — confirm on CT 157); document deploy.

**Step 1:** Inspect the orchestrator's existing bead/schedule definitions on CT 157; mirror the format for a `learnings-extract-weekly` bead that runs `extract.sh` weekly.
**Step 2:** Deploy `learnings-extractor/` to CT 157; create the `learnings-review` Vikunja project (or reuse `operations` with a `learnings-candidate` label — decide at deploy).
**Step 3:** First live run with `--dry-run`, eyeball candidates; then one live run; confirm cards land with evidence + both verdicts.
**Step 4:** **Commit** `feat(learnings-extractor): orchestrator weekly bead + deploy notes` and open the PR.

---

## Verification (whole feature)

- `cd learnings-extractor && python3 -m pytest` → all green.
- `bash extract.sh --dry-run --since 7d` → prints plausible candidates, exit 0, no cards created, no KB files touched.
- One live run → cards in the review project with evidence + both model verdicts; `git status` in every workspace repo clean (the job wrote no tracked files).
- Confirm a forced `SchemaError` path fails loud (no partial cards) and that an empty-friction week advances state + Pushovers cleanly.

## Notes for the implementer
- Packaging: decide the import root early (Task 0). If running from `learnings-extractor/`, either add an `__init__.py` package `learnings_extractor` or set `pythonpath` in pytest config; keep test imports consistent with the choice.
- Never `Write` (overwrite) a learnings file in `apply_candidates.py` — append only (cf. the 2026-05-08 "Write stubbed a learnings file" mistake).
- Verify the live `memory-search` and `vikunja-queue` CLI contracts before wiring the live calls; the unit tests inject fakes precisely so the build doesn't block on them.
