"""memory-search CLI — thin wrapper over memory_search_mcp.core.

  memory-search "how do I rotate a leaked secret"   # recall (top-k)
  memory-search --reindex                            # refresh the index
  memory-search --stats                              # index size
  memory-search "..." --k 10 --json                  # machine-readable
"""
import argparse
import json

from memory_search_mcp import core


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Local semantic recall over Claude memory + learnings")
    ap.add_argument("query", nargs="?", default="")
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--reindex", action="store_true")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if a.reindex:
        r = core.reindex()
        print(f"reindex: +{r['changed']} changed, {r['unchanged']} unchanged, "
              f"-{r['removed']} stale; total={r['total']}")
        return
    if a.stats:
        s = core.stats()
        print(f"collection '{s['collection']}': {s['count']} docs @ {s['db_dir']}")
        return
    if not a.query:
        ap.error("provide a query, or --reindex / --stats")

    rows = core.search(a.query, k=a.k)
    if a.json:
        print(json.dumps(rows, indent=2))
        return
    for r in rows:
        print(f"[{r['score']:.3f}] {r['title']}  ({r['type']})")
        print(f"        {r['file']}")
        if r["desc"]:
            print(f"        {r['desc']}")
    if not rows:
        print("(no results)")


if __name__ == "__main__":
    main()
