"""Friction-signal detection + window extraction over transcript turns.

Stage 1 (deterministic) of the learnings-extractor pipeline. A "friction
window" is the span of turns ``[hit_index - before, hit_index + after]``
around a signal hit. Overlapping windows merge into one.
"""
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
