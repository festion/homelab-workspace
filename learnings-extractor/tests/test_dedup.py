from learnings_extractor.lib import dedup


def fake_search(query, k):
    return [{"score": 0.95, "path": "x"}] if "stale DNS" in query else []


def test_duplicate_dropped():
    cands = [{"headline": "stale DNS thing", "core": "..."}]
    assert dedup.filter_new(cands, search=fake_search, threshold=0.85) == []


def test_novel_kept():
    cands = [{"headline": "brand new pattern", "core": "..."}]
    assert len(dedup.filter_new(cands, search=fake_search, threshold=0.85)) == 1
