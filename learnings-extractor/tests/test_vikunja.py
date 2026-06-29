from learnings_extractor.lib import vikunja


def test_card_body_includes_evidence_and_verdicts():
    body = vikunja.render_card({
        "kind": "learning", "headline": "H", "core": "C", "routing": "global",
        "evidence": ["s1", "s2"], "primary": "draft",
        "crosscheck": {"verdict": "agree"}})
    assert "H" in body and "agree" in body and "s1" in body


def test_conflict_flagged_in_title():
    t = vikunja.card_title({"headline": "H", "crosscheck": {"verdict": "disagree"}})
    assert t.startswith("[CONFLICT]")


def test_agree_title_not_flagged():
    t = vikunja.card_title({"headline": "H", "crosscheck": {"verdict": "agree"}})
    assert not t.startswith("[CONFLICT]") and "H" in t
