"""Smoke tests for the indexing/search core against a temp memory store."""
import importlib


def _fresh_core(tmp_path, monkeypatch):
    mem = tmp_path / "memory"
    learn = tmp_path / "learnings"
    mem.mkdir()
    learn.mkdir()
    (mem / "reference_widget_api.md").write_text(
        "---\nname: Widget API access\n"
        "description: The widget service lives at 10.0.0.5 port 9000, token in vault\n"
        "metadata:\n  type: reference\n---\n\nBearer token rotates monthly.\n",
        encoding="utf-8",
    )
    (mem / "MEMORY.md").write_text("# index — should be skipped\n", encoding="utf-8")
    (learn / "mistakes.md").write_text(
        "# Mistakes\n\n"
        "### Never delete the prod database without a snapshot — 2026-01-01\n"
        "- Wrong: dropped the table. Right: snapshot first.\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("MEMORY_DIR", str(mem))
    monkeypatch.setenv("LEARNINGS_DIR", str(learn))
    monkeypatch.setenv("MEMSEARCH_DB", str(tmp_path / "chroma"))
    import memory_search_mcp.core as core
    return importlib.reload(core)


def test_reindex_counts_memory_and_learnings(tmp_path, monkeypatch):
    core = _fresh_core(tmp_path, monkeypatch)
    r = core.reindex()
    # 1 memory file (MEMORY.md skipped) + 1 learnings entry
    assert r["total"] == 2
    assert r["changed"] == 2
    # Second pass: nothing changed.
    assert core.reindex()["changed"] == 0


def test_search_finds_by_meaning_not_keyword(tmp_path, monkeypatch):
    core = _fresh_core(tmp_path, monkeypatch)
    core.reindex()
    rows = core.search("where does the gadget server run", k=3)
    assert rows and rows[0]["file"] == "reference_widget_api.md"
    rows = core.search("avoid wiping the database", k=3)
    assert any("Never delete the prod database" in r["title"] for r in rows)


def test_read_entry(tmp_path, monkeypatch):
    core = _fresh_core(tmp_path, monkeypatch)
    out = core.read_entry("reference_widget_api.md")
    assert "10.0.0.5" in out["content"]
    assert core.read_entry("nope_missing")["content"] is None
