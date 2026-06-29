"""Stage-2/3 LLM-boundary parsing: schema validation + fail-safe verdict parse.

Stdlib only (hand-rolled validation, no jsonschema dep).

- ``parse_candidates``: the stage-2 (Opus cluster) output must be a JSON list
  of objects each carrying the REQUIRED fields; anything else raises
  ``SchemaError`` (the wrapper retries once, then fails loud — no partial
  cards).
- ``parse_verdict``: the stage-3 (gemini cross-check) verdict. Anything that
  isn't a clean ``agree`` fails safe to ``disagree`` so a garbage verdict
  surfaces as a conflict rather than being silently smoothed into agreement.
"""
import json
import re

REQUIRED = {"kind", "headline", "core", "routing", "evidence_session_ids",
            "occurrence_count"}

_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)


class SchemaError(Exception):
    pass


def _loads_lenient(text):
    """json.loads tolerant of code fences + preamble noise.

    LLM CLIs are imperfectly obedient: ``gemini -o text`` wraps output in
    ```json ... ``` fences and prepends diagnostic lines despite an "output
    only JSON" instruction. Strip fences, then fall back to scanning for the
    first balanced JSON value. Raises ``json.JSONDecodeError`` if none found.
    """
    text = text.strip()
    m = _FENCE.search(text)
    if m:
        text = m.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        for i, ch in enumerate(text):
            if ch in "[{":
                try:
                    obj, _ = json.JSONDecoder().raw_decode(text[i:])
                    return obj
                except json.JSONDecodeError:
                    continue
        raise


def parse_candidates(text):
    try:
        data = _loads_lenient(text)
    except json.JSONDecodeError as e:
        raise SchemaError(f"bad json: {e}")
    if not isinstance(data, list):
        raise SchemaError("expected a list")
    for c in data:
        if not isinstance(c, dict):
            raise SchemaError("each candidate must be an object")
        missing = REQUIRED - set(c)
        if missing:
            raise SchemaError(f"missing fields: {missing}")
    return data


def parse_verdict(text):
    try:
        obj = _loads_lenient(text)
    except json.JSONDecodeError:
        return {"verdict": "disagree", "reason": "unparseable verdict"}
    if not isinstance(obj, dict):
        return {"verdict": "disagree", "reason": "unparseable verdict"}
    v = obj.get("verdict")
    if v not in ("agree", "disagree"):
        return {"verdict": "disagree", "reason": "unparseable verdict"}
    return {"verdict": v, "reason": obj.get("reason", "")}
