# src/memory_search_mcp/server.py
"""Memory Search MCP Server — local semantic recall for Claude Code.

Exposes Claude's own memory store (per-fact memory files) and the learnings
knowledge base as searchable tools. Embeddings run locally (ChromaDB MiniLM),
so recall costs zero API tokens and does not depend on MEMORY.md's hand-curated
index being complete or correct.
"""
import logging
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP

from memory_search_mcp import core

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger(__name__)

mcp = FastMCP("Memory Search")


@mcp.tool()
def memory_recall(query: str, k: int = 8, project: str | None = None) -> dict[str, Any]:
    """Semantically recall the most relevant memories + learnings for a query.

    Use this whenever the loaded MEMORY.md index doesn't already answer a recall
    need — especially for reference/lookup facts (IPs, credential locations, API
    quirks, infra details) and past mistakes/learnings. Matches on meaning, not
    keywords, so natural-language questions work ("how do I rotate a leaked
    secret", "why did my commit land on the wrong branch").

    Indexes the global workspace memory + global learnings AND every project's
    own .claude/learnings across the monorepo. Each hit carries `project`
    ("(global)" or a repo name like "operations"/"stormcrow").

    Returns ranked hits with `score` (≈0..1 similarity), `title`, `type`,
    `project`, `file`, and a short `desc`. Call `memory_read` with a hit's
    `path` (or `file` for global entries) to pull its full text.

    Args:
        query: Natural-language description of what you're trying to recall.
        k: Max number of hits to return (default 8).
        project: Optional repo name to scope to (e.g. "operations"); returns
            that project's learnings plus the global store.
    """
    rows = core.search(query, k=k, project=project)
    return {"query": query, "count": len(rows), "results": rows}


@mcp.tool()
def memory_read(name: str) -> dict[str, Any]:
    """Read the full text of a single memory or learnings file.

    Use after `memory_recall` to expand a promising hit. Accepts a memory
    filename ("reference_pushover_credentials.md" or without ".md") or a
    learnings file base name ("mistakes", "anti-patterns", "environment",
    "validated").

    Args:
        name: Memory filename or learnings base name from a recall hit's `file`.
    """
    return core.read_entry(name)


@mcp.tool()
def memory_reindex() -> dict[str, Any]:
    """Refresh the semantic index (incremental — re-embeds only changed files,
    drops removed ones). Runs automatically at session start; call this after
    writing new memories/learnings within a session to make them recallable now.
    """
    return core.reindex()


@mcp.tool()
def memory_stats() -> dict[str, Any]:
    """Report index size and the directories being indexed."""
    return core.stats()


def main() -> None:
    logger.info("Starting Memory Search MCP server (%s)", core.stats())
    mcp.run()


if __name__ == "__main__":
    main()
