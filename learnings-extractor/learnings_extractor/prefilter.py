"""Stage 1: scan Claude Code transcripts, extract redacted friction windows.

Deterministic, pure-stdlib. ``scan`` maintains a high-water mark (max mtime
processed) in a state file so unchanged transcripts are skipped on the next run.

NOTE: ``scan`` advances the high-water mark on return. The wrapper (extract.sh)
must call ``scan`` once per run and treat any downstream failure as
"re-process next week" by only persisting the state on full success. The unit
test exercises the simple in-place write; the transactional guard lives in the
wrapper.
"""
import json
from pathlib import Path

from learnings_extractor.lib import signals
from learnings_extractor.lib.redact import redact

# Cap per-turn content in an excerpt. Friction turns can embed huge tool-output
# dumps (e.g. a 34KB Explore result); the failure-mode signal lives in the first
# few hundred chars, and unbounded excerpts blow past the cluster model's stdin /
# context limits (a 7-day cold-start scan produced a ~20MB prompt).
MAX_TURN_CHARS = 600


def _clip(text):
    if len(text) <= MAX_TURN_CHARS:
        return text
    return text[:MAX_TURN_CHARS] + " …[truncated]"


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
            f"[{turns[i]['role']}] {_clip(str(turns[i]['content']))}"
            for i in range(w.start, w.end + 1)))
        out.append({"session": Path(path).stem,
                    "kinds": list(w.kinds),
                    "excerpt": excerpt})
    return out


def scan(dirs, state_path, since_mtime=0):
    if since_mtime is None:
        since_mtime = (json.loads(Path(state_path).read_text()).get("hwm", 0)
                       if Path(state_path).exists() else 0)
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
