"""Stages 2-5 orchestration (invoked by extract.sh under a timeout).

Flow: prefilter.scan -> claude -p cluster -> gemini cross-check -> dedup vs KB
-> Vikunja cards (or print, in --dry-run).

Transactional state: ``prefilter.scan`` advances the high-water mark as a side
effect, but the design requires it to advance ONLY on full success. We snapshot
the state file before scanning and restore it if anything downstream raises, so
a crash re-processes the same week instead of silently skipping it. An empty
week IS success — the advanced mark is kept.

External CLIs are resolved by name (overridable via CLAUDE_BIN / GEMINI_BIN) so
the smoke test can stub them on PATH.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from learnings_extractor import prefilter
from learnings_extractor.lib import candidates as candidates_mod
from learnings_extractor.lib import dedup, vikunja

PROMPTS = Path(__file__).parent.parent / "prompts"
CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "claude")
GEMINI_BIN = os.environ.get("GEMINI_BIN", "gemini")


def _cluster(windows, model):
    """Stage 2: claude -p clusters windows -> candidates JSON. Retry once, then fail loud."""
    prompt = (PROMPTS / "cluster.md").read_text() + "\n\nINPUT:\n" + json.dumps(windows)
    last_err = None
    for attempt in (1, 2):
        out = subprocess.run([CLAUDE_BIN, "-p", "--model", model],
                             input=prompt, capture_output=True, text=True, timeout=900)
        try:
            return candidates_mod.parse_candidates(out.stdout)
        except candidates_mod.SchemaError as e:
            last_err = e
    raise candidates_mod.SchemaError(f"cluster output unparseable after retry: {last_err}")


def _crosscheck(candidate):
    """Stage 3: gemini re-judges one candidate; returns raw verdict text."""
    prompt = (PROMPTS / "crosscheck.md").read_text() + "\n\nCANDIDATE:\n" + json.dumps(candidate)
    out = subprocess.run([GEMINI_BIN, "-o", "text"],
                         input=prompt, capture_output=True, text=True, timeout=300)
    return out.stdout


def _parse_since(s):
    if not s:
        return None
    s = s.strip().lower()
    mult = {"d": 86400, "h": 3600, "m": 60, "s": 1}
    if s[-1] in mult:
        return time.time() - float(s[:-1]) * mult[s[-1]]
    return float(s)  # bare number = absolute mtime cutoff


def run(dirs, state_path, project_id, dry_run, since_mtime=None,
        model=None, out=sys.stdout):
    model = model or os.environ.get("EXTRACT_MODEL", "claude-opus-4-8")
    state_path = Path(state_path)
    prev = state_path.read_text() if state_path.exists() else None

    def _rollback():
        if prev is None:
            state_path.unlink(missing_ok=True)
        else:
            state_path.write_text(prev)

    try:
        windows = prefilter.scan(dirs, state_path=state_path, since_mtime=since_mtime)
        if not windows:
            print("no friction windows this week (state advanced)", file=out)
            return 0

        cands = _cluster(windows, model)
        for c in cands:
            c["crosscheck"] = candidates_mod.parse_verdict(_crosscheck(c))
        survivors = dedup.filter_new(cands)

        if not survivors:
            print(f"{len(cands)} candidate(s), all deduped against KB; no cards", file=out)
            return 0

        for c in survivors:
            if dry_run:
                print(json.dumps({"title": vikunja.card_title(c),
                                  "body": vikunja.render_card(c)}), file=out)
            else:
                vikunja.create_card(project_id, c)
        print(f"{len(survivors)} card(s) "
              f"{'printed (dry-run)' if dry_run else 'created'}", file=out)
        return 0
    except Exception:
        _rollback()  # advance ONLY on full success
        raise


def _default_dirs():
    base = Path(os.path.expanduser("~/.claude/projects"))
    return [str(p) for p in base.glob("*")] if base.exists() else []


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--transcripts", nargs="+", default=None,
                    help="transcript dirs (default: ~/.claude/projects/*)")
    ap.add_argument("--state", default=str(Path(__file__).parent.parent / "state" / "last_run.json"))
    ap.add_argument("--project-id", type=int, default=0,
                    help="Vikunja learnings-review project id (live runs)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--since", default=None, help="e.g. 7d, 48h (default: state high-water mark)")
    ap.add_argument("--model", default=None)
    args = ap.parse_args(argv)

    dirs = args.transcripts if args.transcripts is not None else _default_dirs()
    return run(dirs, state_path=args.state, project_id=args.project_id,
               dry_run=args.dry_run, since_mtime=_parse_since(args.since),
               model=args.model)


if __name__ == "__main__":
    raise SystemExit(main())
