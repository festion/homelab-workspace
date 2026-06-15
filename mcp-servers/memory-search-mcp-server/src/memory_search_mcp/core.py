"""Indexing + search core for the memory-search MCP server.

Single source of truth shared by the CLI (`memory_search_mcp.cli`) and the MCP
server (`memory_search_mcp.server`). Embeddings run locally via ChromaDB's
default MiniLM ONNX model — no API tokens are spent on indexing or retrieval.

Paths are overridable via env vars so the server can be pointed at any memory
store (defaults match the dev box):
  MEMORY_DIR     directory of *.md memory files (one fact per file)
  LEARNINGS_DIR  directory of *.md learnings files (split per "### " entry)
  MEMSEARCH_DB   ChromaDB persistence dir
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
DB_DIR = os.environ.get(
    "MEMSEARCH_DB", os.path.expanduser("~/.cache/memory-search/chroma")
)
COLLECTION = "memory"

# Files in MEMORY_DIR that are indexes/backups, not recallable content.
_SKIP = {"MEMORY.md", "MEMORY-archive.md"}


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
                "mtime": str(os.path.getmtime(path)),
            }
    if os.path.isdir(LEARNINGS_DIR):
        for path in sorted(glob.glob(os.path.join(LEARNINGS_DIR, "*.md"))):
            base = os.path.basename(path)[:-3]
            text = _read(path)
            mt = str(os.path.getmtime(path))
            parts = re.split(r"(?m)^### ", text)
            for i, part in enumerate(parts):
                part = part.strip()
                if i == 0 or not part:
                    continue  # i==0 is the file preamble, not a recall entry
                title = part.splitlines()[0].strip("# ").strip()
                doc = ("### " + part)[:8000]
                yield f"learn:{base}#{i}", doc, {
                    "source": "learnings", "file": base, "path": path,
                    "title": title[:120], "desc": title[:300],
                    "type": f"learning/{base}", "mtime": mt,
                }


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


def search(query: str, k: int = 8) -> list[dict]:
    """Return up to k semantically-relevant entries, most-relevant first.
    Auto-indexes on first use if the collection is empty."""
    coll = _collection()
    if coll.count() == 0:
        reindex()
        coll = _collection()
    res = coll.query(query_texts=[query], n_results=max(1, k),
                     include=["metadatas", "distances"])
    rows = []
    for md, dist in zip(res["metadatas"][0], res["distances"][0]):
        rows.append({
            "score": round(1 - dist / 2, 3),  # cosine distance -> ~0..1 similarity
            "title": md.get("title", ""),
            "type": md.get("type", ""),
            "file": md.get("file", ""),
            "path": md.get("path", ""),
            "desc": md.get("desc", ""),
        })
    return rows


def read_entry(name: str) -> dict:
    """Return the full text of a memory file (e.g. 'reference_pushover_credentials.md'
    or without the .md) or a learnings file ('mistakes'/'anti-patterns'/...)."""
    candidates = []
    if name.endswith(".md"):
        candidates.append(os.path.join(MEMORY_DIR, name))
    else:
        candidates.append(os.path.join(MEMORY_DIR, name + ".md"))
        candidates.append(os.path.join(LEARNINGS_DIR, name + ".md"))
        candidates.append(os.path.join(LEARNINGS_DIR, name.replace("learning/", "") + ".md"))
    for path in candidates:
        if os.path.isfile(path):
            return {"name": name, "path": path, "content": _read(path)}
    return {"name": name, "path": None, "content": None,
            "error": f"not found in {MEMORY_DIR} or {LEARNINGS_DIR}"}


def stats() -> dict:
    return {"collection": COLLECTION, "count": _collection().count(),
            "db_dir": DB_DIR, "memory_dir": MEMORY_DIR,
            "learnings_dir": LEARNINGS_DIR}
