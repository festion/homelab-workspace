"""Smoke tests for the indexing/search core against a temp memory store."""
import importlib


def _fresh_core(tmp_path, monkeypatch):
    mem = tmp_path / "memory"
    learn = tmp_path / "learnings"
    ws = tmp_path / "workspace"
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
    # A per-project learnings file in the workspace (single-file form), plus a
    # pruned node_modules copy that MUST be ignored.
    proj = ws / "acme-svc" / ".claude"
    proj.mkdir(parents=True)
    (proj / "learnings.md").write_text(
        "# acme-svc learnings\n\n"
        "### The acme widget queue drops messages over 256KB — chunk them — 2026-02-02\n"
        "- Wrong: sent a 1MB blob. Right: split into 200KB chunks.\n",
        encoding="utf-8",
    )
    nm = ws / "acme-svc" / "node_modules" / "pkg" / ".claude"
    nm.mkdir(parents=True)
    (nm / "learnings.md").write_text("### should be pruned — 2026-01-01\n- x\n", encoding="utf-8")
    monkeypatch.setenv("MEMORY_DIR", str(mem))
    monkeypatch.setenv("LEARNINGS_DIR", str(learn))
    monkeypatch.setenv("WORKSPACE_DIR", str(ws))
    monkeypatch.setenv("MEMSEARCH_DB", str(tmp_path / "chroma"))
    import memory_search_mcp.core as core
    return importlib.reload(core)


def test_reindex_counts_memory_learnings_and_projects(tmp_path, monkeypatch):
    core = _fresh_core(tmp_path, monkeypatch)
    r = core.reindex()
    # 1 memory file (MEMORY.md skipped) + 1 global learning + 1 project learning
    # (node_modules copy pruned).
    assert r["total"] == 3
    assert r["changed"] == 3
    assert core.reindex()["changed"] == 0  # second pass: nothing changed


def test_search_finds_by_meaning_not_keyword(tmp_path, monkeypatch):
    core = _fresh_core(tmp_path, monkeypatch)
    core.reindex()
    rows = core.search("where does the gadget server run", k=3)
    assert rows and rows[0]["file"] == "reference_widget_api.md"
    rows = core.search("avoid wiping the database", k=3)
    assert any("Never delete the prod database" in r["title"] for r in rows)


def test_project_learnings_indexed_and_filterable(tmp_path, monkeypatch):
    core = _fresh_core(tmp_path, monkeypatch)
    core.reindex()
    # The project learning is recallable and tagged with its project.
    rows = core.search("large payload size limit on the queue", k=5)
    hit = next((r for r in rows if "acme widget queue" in r["title"]), None)
    assert hit is not None and hit["project"] == "acme-svc"
    # node_modules copy was pruned.
    assert core.stats()["projects"].get("acme-svc") == 1
    # project filter returns project + global, never the wrong project.
    rows = core.search("database", k=5, project="acme-svc")
    assert all(r["project"] in ("acme-svc", "(global)") for r in rows)


def test_read_entry(tmp_path, monkeypatch):
    core = _fresh_core(tmp_path, monkeypatch)
    core.reindex()
    out = core.read_entry("reference_widget_api.md")
    assert "10.0.0.5" in out["content"]
    # per-project learning is read via its absolute path (from a recall hit)
    hit = core.search("acme widget queue 256KB", k=5)[0]
    assert "256KB" in core.read_entry(hit["path"])["content"]
    assert core.read_entry("nope_missing")["content"] is None
