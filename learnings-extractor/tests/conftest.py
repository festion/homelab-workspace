import json

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
