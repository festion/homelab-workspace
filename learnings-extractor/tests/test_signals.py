from learnings_extractor.lib import signals


def turns(*pairs):
    return [{"role": r, "content": c, "type": r} for r, c in pairs]


def test_user_correction_detected():
    t = turns(("user", "do X"), ("assistant", "done"), ("user", "no, that's wrong"))
    hits = signals.find_hits(t)
    assert any(h.kind == "correction" and h.index == 2 for h in hits)


def test_no_in_assistant_turn_not_detected():
    t = turns(("user", "do X"), ("assistant", "no problem, done"))
    assert [h for h in signals.find_hits(t) if h.kind == "correction"] == []


def test_no_inside_codeblock_not_detected():
    t = turns(("user", "```\nif no: pass\n```"))
    assert [h for h in signals.find_hits(t) if h.kind == "correction"] == []


def test_interrupt_detected():
    t = turns(("user", "[Request interrupted by user]"))
    assert any(h.kind == "interrupt" for h in signals.find_hits(t))


def test_window_clamps_at_start_and_end():
    t = turns(("user", "no, wrong"))
    w = signals.windows(t, before=2, after=2)
    assert w[0].start == 0 and w[0].end == 0


def test_overlapping_hits_merge_to_one_window():
    t = turns(("user", "no"), ("assistant", "ok"), ("user", "wrong"))
    w = signals.windows(t, before=1, after=1)
    assert len(w) == 1  # the two correction hits merge
