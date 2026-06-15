# memory-search-mcp-server

Local semantic recall over Claude Code's persistent memory and learnings, as MCP
tools. Embeddings run **locally** (ChromaDB's default MiniLM ONNX model), so both
indexing and retrieval cost **zero API tokens**. Recall matches on *meaning*, not
keywords, and indexes **every** memory file and learnings entry on disk — so it
does not depend on `MEMORY.md`'s hand-curated index being complete or correct.

Coverage spans the whole monorepo: the **global** workspace memory + global
learnings, **and** each project's own `.claude/learnings` (e.g. `operations`,
`stormcrow`, `home-assistant-config`). Every hit is tagged with its `project`
(`(global)` or the repo name); `memory_recall(..., project="operations")` scopes
to that repo's learnings plus global.

## Why

The auto-loaded `MEMORY.md` index has a size ceiling (it gets silently truncated
when too large) and drifts (orphaned files, stale pointers). This server lets the
bulk of reference/lookup memory live outside the always-loaded index while staying
fully recallable on demand — and surfaces per-project learnings that were never in
`MEMORY.md` at all.

## Tools

| Tool | Purpose |
|---|---|
| `memory_recall(query, k=8, project=None)` | Rank the most relevant memories + learnings for a query; optional `project` scopes to that repo + global. |
| `memory_read(name)` | Read the full text of a hit — pass a recall hit's `path` (works for per-project learnings) or a global memory/learnings name. |
| `memory_reindex()` | Incrementally refresh the index (re-embeds only changed files). |
| `memory_stats()` | Index size + per-project doc breakdown. |

## Layout & config

```
src/memory_search_mcp/
  core.py     indexing + search (single source of truth)
  server.py   FastMCP server (memory-search-mcp entry point)
  cli.py      CLI (memory-search entry point)
```

Paths are overridable via env vars (defaults are the dev box):
`MEMORY_DIR`, `LEARNINGS_DIR`, `WORKSPACE_DIR` (monorepo root, walked for
per-project `.claude/learnings`), `MEMSEARCH_DB`.

## Install / run

```sh
python3 -m venv .venv && .venv/bin/pip install -e .
.venv/bin/memory-search --reindex          # build the index (first run downloads MiniLM once)
.venv/bin/memory-search "rotate a leaked secret"
.venv/bin/pytest -q                         # smoke tests (isolated temp store)
```

Registered as an MCP server with:
`claude mcp add -s user memory-search -- <venv>/bin/memory-search-mcp`

A SessionStart hook (`~/.claude/hooks/memory-search-reindex.sh`) keeps the index
fresh and reminds the agent that reference facts are recalled via `memory-search`.
