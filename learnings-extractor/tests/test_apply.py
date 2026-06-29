from learnings_extractor import apply_candidates as ap


def test_writes_archive_body_and_index_headline(tmp_path):
    idx = tmp_path / "anti-patterns.md"
    arc = tmp_path / "anti-patterns-archive.md"
    idx.write_text("# Index\n")
    arc.write_text("# Archive\n")
    ap.write_entry(idx, arc, headline="### New rule — 2026-06-29", body="full body text")
    assert "### New rule" in idx.read_text()
    assert "full body text" in arc.read_text()
    assert "full body text" not in idx.read_text()  # body NEVER in @-imported index


def test_headline_byte_identical_between_files(tmp_path):
    idx = tmp_path / "i.md"
    arc = tmp_path / "a.md"
    idx.write_text("")
    arc.write_text("")
    h = "### Title — 2026-06-29"
    ap.write_entry(idx, arc, headline=h, body="x")
    assert h in idx.read_text() and h in arc.read_text()  # anchor for grep/memory-search


def test_write_entry_appends_does_not_overwrite(tmp_path):
    idx = tmp_path / "i.md"
    arc = tmp_path / "a.md"
    idx.write_text("# Existing index\n### Old headline — 2026-01-01\n")
    arc.write_text("# Existing archive\nold body\n")
    ap.write_entry(idx, arc, headline="### New — 2026-06-29", body="new body")
    # prior content preserved (append-only, never Write-overwrite)
    assert "Old headline" in idx.read_text() and "old body" in arc.read_text()
