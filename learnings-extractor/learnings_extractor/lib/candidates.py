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

REQUIRED = {"kind", "headline", "core", "routing", "evidence_session_ids",
            "occurrence_count"}


class SchemaError(Exception):
    pass


def parse_candidates(text):
    try:
        data = json.loads(text)
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
        obj = json.loads(text)
    except json.JSONDecodeError:
        return {"verdict": "disagree", "reason": "unparseable verdict"}
    if not isinstance(obj, dict):
        return {"verdict": "disagree", "reason": "unparseable verdict"}
    v = obj.get("verdict")
    if v not in ("agree", "disagree"):
        return {"verdict": "disagree", "reason": "unparseable verdict"}
    return {"verdict": v, "reason": obj.get("reason", "")}
