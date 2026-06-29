import pytest

from learnings_extractor.lib import candidates

VALID = ('[{"kind":"learning","headline":"H","core":"C","routing":"global",'
         '"evidence_session_ids":["s1"],"occurrence_count":2}]')


def test_valid_parses():
    assert len(candidates.parse_candidates(VALID)) == 1


def test_malformed_raises():
    with pytest.raises(candidates.SchemaError):
        candidates.parse_candidates("not json")


def test_missing_field_raises():
    with pytest.raises(candidates.SchemaError):
        candidates.parse_candidates('[{"kind":"learning"}]')


def test_garbage_verdict_is_conflict():
    # fail-safe toward surfacing: unparseable verdict counts as disagreement
    assert candidates.parse_verdict("???")["verdict"] == "disagree"


def test_agree_verdict():
    assert candidates.parse_verdict('{"verdict":"agree","reason":"r"}')["verdict"] == "agree"
