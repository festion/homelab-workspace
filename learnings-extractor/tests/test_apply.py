from learnings_extractor import apply_candidates as ap


def test_classify_routes_never_to_anti_patterns():
    assert ap.classify_file({"headline": "Never push to main", "core": ""}) == "anti-patterns"


def test_classify_defaults_to_environment():
    assert ap.classify_file({"headline": "claude -p caps stdin at 10MB", "core": "x"}) == "environment"


def test_target_files_global_vs_project(tmp_path):
    gi, ga = ap.target_files({"routing": "global", "headline": "x stale y", "core": ""},
                             global_root=str(tmp_path / "g"))
    assert gi.name == "environment.md" and ga.name == "environment-archive.md"
    pi, _ = ap.target_files({"routing": "operations", "headline": "never x", "core": ""},
                            workspace=str(tmp_path / "ws"))
    assert "operations" in str(pi) and pi.name == "anti-patterns.md"


def test_build_headline_adds_date_once():
    h = ap.build_headline({"headline": "Some gotcha"}, "2026-06-29")
    assert h == "### Some gotcha — 2026-06-29"
    h2 = ap.build_headline({"headline": "Dated thing — 2026-01-01"}, "2026-06-29")
    assert h2.endswith("2026-01-01")  # not double-dated


def test_is_probable_dup_detects_overlap():
    existing = ["Claude Code --allowedTools Bash rules are LITERAL PREFIXES — 2026-06-05"]
    assert ap.is_probable_dup("### Claude Code --allowedTools Bash rules are LITERAL PREFIXES, embedded star", existing)
    assert not ap.is_probable_dup("### Completely unrelated DHCP lease quirk", existing)


def test_parse_card_recovers_entity_escaped_core():
    # the rendered core is HTML-escaped; apostrophes must not truncate it
    body = ("<h3>H headline</h3>"
            "<p><b>Kind:</b> learning &nbsp; <b>Routing:</b> operations</p>"
            "<p><b>Core:</b> don&#x27;t do X; it&#x27;s wrong</p>"
            "<p><b>Evidence sessions:</b></p><ul><li>s1</li><li>s2</li></ul>")
    c = ap.parse_card({"id": 1, "description": body, "title": "[Learning] H"})
    assert c["core"] == "don't do X; it's wrong"
    assert c["routing"] == "operations"
    assert c["evidence_session_ids"] == ["s1", "s2"]


def test_index_gets_core_archive_gets_body(tmp_path):
    idx = tmp_path / "environment.md"
    arc = tmp_path / "environment-archive.md"
    idx.write_text("")
    arc.write_text("")
    ap.write_entry(idx, arc, "### H — 2026-06-29", "- full body line\n- more", core="one-line core")
    assert "one-line core" in idx.read_text() and "full body line" not in idx.read_text()
    assert "full body line" in arc.read_text()


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
