"""Stage 4: drop candidates that duplicate an already-captured KB entry.

Uses the local ``memory-search`` CLI (ChromaDB + local embeddings, zero API
tokens). The search function is injectable so unit tests run against a fake and
never touch the live index.

Verified live contract (2026-06-29): ``memory-search QUERY --json --k K`` emits
a JSON list of hits, each with a numeric ``score`` and a ``path``.
"""
import json
import subprocess


def _cli_search(query, k):
    out = subprocess.run(["memory-search", query, "--json", "--k", str(k)],
                         capture_output=True, text=True, timeout=60)
    return json.loads(out.stdout) if out.stdout.strip() else []


def filter_new(candidates, search=_cli_search, threshold=0.85, k=3):
    kept = []
    for c in candidates:
        hits = search(f"{c['headline']} {c.get('core', '')}", k)
        if not any(h.get("score", 0) >= threshold for h in hits):
            kept.append(c)
    return kept
