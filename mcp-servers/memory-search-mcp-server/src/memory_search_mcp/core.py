"""Indexing + search core for the memory-search MCP server.

Single source of truth shared by the CLI (`memory_search_mcp.cli`) and the MCP
server (`memory_search_mcp.server`). Embeddings run locally via ChromaDB's
default MiniLM ONNX model — no API tokens are spent on indexing or retrieval.

Paths are overridable via env vars so the server can be pointed at any memory
store (defaults match the dev box):
  MEMORY_DIR     directory of *.md memory files (one fact per file)
  LEARNINGS_DIR  directory of *.md global learnings files (split per "### " entry)
  WORKSPACE_DIR  monorepo root; per-project .claude/learnings are also indexed
  MEMSEARCH_DB   ChromaDB persistence dir

Every doc carries a `project` metadata key: "(global)" for the workspace memory
store + global learnings, or the project path (e.g. "operations", "stormcrow")
for per-project .claude/learnings. search(..., project=X) returns X's entries
plus global ones.
"""
from __future__ import annotations

import glob
import os
import re

MEMORY_DIR = os.environ.get(
    "MEMORY_DIR",
    "/home/dev/.claude/projects/-home-dev-workspace/memory",
)
LEARNINGS_DIR = os.environ.get("LEARNINGS_DIR", "/home/dev/.claude/learnings")
WORKSPACE_DIR = os.environ.get("WORKSPACE_DIR", "/home/dev/workspace")
DB_DIR = os.environ.get(
    "MEMSEARCH_DB", os.path.expanduser("~/.cache/memory-search/chroma")
)
COLLECTION = "memory"
GLOBAL = "(global)"

# Files in MEMORY_DIR that are indexes/backups, not recallable content.
_SKIP = {"MEMORY.md", "MEMORY-archive.md"}
# Dirs never descended into when walking WORKSPACE_DIR for project learnings.
_PRUNE = {"node_modules", ".git", ".worktrees", ".venv", "venv", "__pycache__",
          "dist", "build", ".next", "coverage", ".cache", "target", ".pytest_cache"}


def _client():
    import chromadb

    os.makedirs(DB_DIR, exist_ok=True)
    return chromadb.PersistentClient(path=DB_DIR)


def _collection(client=None):
    client = client or _client()
    # Default embedding_function = ONNXMiniLM_L6_V2 (local, downloaded once).
    return client.get_or_create_collection(COLLECTION)


def _frontmatter(text: str) -> tuple[str, str, str]:
    """Pull (name, description, type) from a memory file's YAML frontmatter."""
    name = desc = mtype = ""
    m = re.search(r"^name:\s*(.+)$", text, re.M)
    if m:
        name = m.group(1).strip().removeprefix("name:").strip()
    m = re.search(r"^description:\s*(.+)$", text, re.M)
    if m:
        desc = m.group(1).strip().strip('"')
    m = re.search(r"^\s*type:\s*(.+)$", text, re.M)
    if m:
        mtype = m.group(1).strip()
    return name, desc, mtype


def iter_docs():
    """Yield (id, document, metadata) for every memory file + learnings entry."""
    if os.path.isdir(MEMORY_DIR):
        for path in sorted(glob.glob(os.path.join(MEMORY_DIR, "*.md"))):
            fn = os.path.basename(path)
            if fn in _SKIP or fn.endswith(".bak"):
                continue
            text = _read(path)
            name, desc, mtype = _frontmatter(text)
            title = name or fn[:-3]
            doc = f"{title}\n{desc}\n{text}"[:8000]
            yield fn, doc, {
                "source": "memory", "file": fn, "path": path,
                "title": title, "desc": desc[:300], "type": mtype or "memory",
                "project": GLOBAL, "mtime": str(os.path.getmtime(path)),
            }
    # Global learnings KB.
    if os.path.isdir(LEARNINGS_DIR):
        for path in sorted(glob.glob(os.path.join(LEARNINGS_DIR, "*.md"))):
            base = os.path.basename(path)[:-3]
            yield from _emit_learning_entries(path, base, GLOBAL, f"learn:{base}")
    # Per-project .claude/learnings across the monorepo.
    yield from _iter_project_learnings()


def _emit_learning_entries(path, base, project, id_prefix):
    """Split a learnings file into per-'### ' entries and yield index docs."""
    text = _read(path)
    mt = str(os.path.getmtime(path))
    type_label = f"learning/{base}" if project == GLOBAL else f"{project}/learning/{base}"
    parts = re.split(r"(?m)^### ", text)
    for i, part in enumerate(parts):
        part = part.strip()
        if i == 0 or not part:
            continue  # i==0 is the file preamble, not a recall entry
        title = part.splitlines()[0].strip("# ").strip()
        doc = ("### " + part)[:8000]
        yield f"{id_prefix}#{i}", doc, {
            "source": "learnings", "file": base, "path": path,
            "title": title[:120], "desc": title[:300],
            "type": type_label, "project": project, "mtime": mt,
        }


def _iter_project_learnings():
    """Walk WORKSPACE_DIR for per-project .claude/learnings (file or dir),
    tagging each entry with its source project (relpath of the .claude parent)."""
    if not os.path.isdir(WORKSPACE_DIR):
        return
    for root, dirs, _files in os.walk(WORKSPACE_DIR):
        dirs[:] = [d for d in dirs if d not in _PRUNE]
        if os.path.basename(root) != ".claude":
            continue
        project = os.path.relpath(os.path.dirname(root), WORKSPACE_DIR)
        # Single-file form: <proj>/.claude/learnings.md
        lm = os.path.join(root, "learnings.md")
        if os.path.isfile(lm):
            yield from _emit_learning_entries(lm, "learnings", project,
                                              f"proj:{project}:learnings")
        # Split form: <proj>/.claude/learnings/*.md
        ldir = os.path.join(root, "learnings")
        if os.path.isdir(ldir):
            for path in sorted(glob.glob(os.path.join(ldir, "*.md"))):
                base = os.path.basename(path)[:-3]
                yield from _emit_learning_entries(path, base, project,
                                                  f"proj:{project}:{base}")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def reindex() -> dict:
    """Incrementally refresh the index; returns counts. Re-embeds only files
    whose mtime changed, and drops ids whose source file/entry is gone."""
    coll = _collection()
    existing = {}
    got = coll.get(include=["metadatas"])
    for _id, md in zip(got["ids"], got["metadatas"]):
        existing[_id] = (md or {}).get("mtime")
    ids, docs, metas, seen = [], [], [], set()
    changed = unchanged = 0
    for _id, doc, md in iter_docs():
        seen.add(_id)
        if existing.get(_id) == md["mtime"]:
            unchanged += 1
            continue
        ids.append(_id); docs.append(doc); metas.append(md); changed += 1
    stale = [i for i in existing if i not in seen]
    if stale:
        coll.delete(ids=stale)
    for j in range(0, len(ids), 100):
        coll.upsert(ids=ids[j:j + 100], documents=docs[j:j + 100],
                    metadatas=metas[j:j + 100])
    return {"changed": changed, "unchanged": unchanged,
            "removed": len(stale), "total": coll.count()}


def search(query: str, k: int = 8, project: str | None = None) -> list[dict]:
    """Return up to k semantically-relevant entries, most-relevant first.
    Auto-indexes on first use if the collection is empty. If `project` is given,
    restrict to that project's entries plus the global store."""
    coll = _collection()
    if coll.count() == 0:
        reindex()
        coll = _collection()
    where = {"project": {"$in": [project, GLOBAL]}} if project else None
    res = coll.query(query_texts=[query], n_results=max(1, k), where=where,
                     include=["metadatas", "distances"])
    rows = []
    for md, dist in zip(res["metadatas"][0], res["distances"][0]):
        rows.append({
            "score": round(1 - dist / 2, 3),  # cosine distance -> ~0..1 similarity
            "title": md.get("title", ""),
            "type": md.get("type", ""),
            "project": md.get("project", ""),
            "file": md.get("file", ""),
            "path": md.get("path", ""),
            "desc": md.get("desc", ""),
        })
    return rows


def read_entry(name: str) -> dict:
    """Return the full text of a recall hit. Accepts an absolute path (from a
    hit's `path` — works for per-project learnings), a memory filename
    ('reference_x.md' or without .md), or a global learnings base name
    ('mistakes'/'anti-patterns'/...)."""
    candidates = []
    if os.path.isabs(name):
        candidates.append(name)
    elif name.endswith(".md"):
        candidates.append(os.path.join(MEMORY_DIR, name))
    else:
        candidates.append(os.path.join(MEMORY_DIR, name + ".md"))
        candidates.append(os.path.join(LEARNINGS_DIR, name + ".md"))
        candidates.append(os.path.join(LEARNINGS_DIR, name.replace("learning/", "") + ".md"))
    for path in candidates:
        if os.path.isfile(path):
            return {"name": name, "path": path, "content": _read(path)}
    return {"name": name, "path": None, "content": None,
            "error": f"not found (tried absolute path, {MEMORY_DIR}, {LEARNINGS_DIR}); "
                     f"pass a recall hit's full `path` for per-project learnings"}


def stats() -> dict:
    coll = _collection()
    got = coll.get(include=["metadatas"])
    by_project: dict[str, int] = {}
    for md in got["metadatas"]:
        by_project[(md or {}).get("project", "?")] = by_project.get((md or {}).get("project", "?"), 0) + 1
    return {"collection": COLLECTION, "count": coll.count(),
            "db_dir": DB_DIR, "memory_dir": MEMORY_DIR,
            "learnings_dir": LEARNINGS_DIR, "workspace_dir": WORKSPACE_DIR,
            "projects": dict(sorted(by_project.items(), key=lambda x: -x[1]))}
