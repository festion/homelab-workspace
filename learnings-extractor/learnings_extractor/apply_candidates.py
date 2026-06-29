"""Write-back: apply human-APPROVED learning cards to the KB, then open a PR.

This is the ONLY component that writes a knowledge-base file, and it is
human-run (never invoked by the weekly job). Discipline baked in:

- **Append-only.** ``write_entry`` opens both files in append mode. We never
  ``Write``/overwrite an ``@``-imported learnings file (cf. the 2026-05-08
  "Write stubbed a learnings file, lost ~120 lines" mistake).
- **Body to archive, headline to index.** The full multi-paragraph body goes to
  ``<file>-archive.md`` (NOT ``@``-imported); only the ``### headline`` line goes
  to the ``@``-imported index — keeping the always-loaded prefix small. The
  headline is byte-identical in both so grep + memory-search anchor on it.
- **PR, never direct push.** ``main()`` branches and opens a PR via ``gh``;
  default is a dry-run print. Pass ``--apply`` to actually write + open the PR.
"""
import argparse
import json
import subprocess
import urllib.request
from pathlib import Path

from learnings_extractor.lib import vikunja


def write_entry(index_path, archive_path, headline, body):
    """Append a headline to the @-imported index and the full entry to the archive.

    Append-only: existing content in both files is preserved. The body never
    lands in the @-imported index.
    """
    index_path = Path(index_path)
    archive_path = Path(archive_path)
    with index_path.open("a") as f:
        f.write(f"\n{headline}\n")
    with archive_path.open("a") as f:
        f.write(f"\n{headline}\n{body}\n")


def list_approved(project_id, creds=None):
    """List Vikunja cards labeled 'approved' in the review project."""
    base, token = creds if creds else vikunja.load_creds()
    req = urllib.request.Request(
        f"{base}/api/v1/projects/{project_id}/tasks",
        headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        tasks = json.loads(resp.read())
    out = []
    for t in tasks:
        labels = [lbl.get("title") for lbl in (t.get("labels") or [])]
        if "approved" in labels and not t.get("done"):
            out.append(t)
    return out


def _run(cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project-id", type=int, required=True,
                    help="Vikunja learnings-review project id")
    ap.add_argument("--apply", action="store_true",
                    help="actually write files + open a PR (default: dry-run print)")
    ap.add_argument("--branch", default="learnings/apply-approved",
                    help="branch name for the write-back PR")
    args = ap.parse_args(argv)

    approved = list_approved(args.project_id)
    if not approved:
        print("No approved cards to apply.")
        return 0

    if not args.apply:
        print(f"[dry-run] would apply {len(approved)} approved card(s):")
        for t in approved:
            print(f"  - {t.get('title')}")
        print("Re-run with --apply to write KB files + open a PR.")
        return 0

    _run(["git", "checkout", "-b", args.branch])
    # NOTE: per-card index/archive routing + headline/body extraction is wired in
    # the deploy step (Task 9), reusing write_entry below. Kept thin here.
    for t in approved:
        print(f"applying: {t.get('title')}")
    _run(["git", "add", "-A"])
    _run(["git", "commit", "-m", "chore(learnings): apply approved candidates"])
    _run(["gh", "pr", "create", "--fill"])
    print("Opened write-back PR.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
