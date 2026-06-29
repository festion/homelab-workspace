import json

from learnings_extractor import prefilter


def test_clean_session_yields_no_windows(transcript):
    p = transcript([("user", "do X"), ("assistant", "done")])
    assert prefilter.process_file(p) == []


def test_friction_session_yields_window(transcript):
    p = transcript([("user", "do X"), ("assistant", "done"), ("user", "no that's wrong")])
    out = prefilter.process_file(p)
    assert len(out) == 1 and "correction" in out[0]["kinds"]


def test_excerpt_is_redacted(transcript):
    p = transcript([("user", "use sk-ant-secrettoken123456"), ("user", "no wrong")])
    out = prefilter.process_file(p)
    assert "sk-ant" not in json.dumps(out)


def test_high_water_mark_skips_unchanged(tmp_path, transcript):
    p = transcript([("user", "no wrong")])
    state = tmp_path / "state.json"
    first = prefilter.scan([p.parent], state_path=state, since_mtime=0)
    second = prefilter.scan([p.parent], state_path=state, since_mtime=None)  # reads state
    assert first and second == []
