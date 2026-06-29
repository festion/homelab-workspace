"""Write-back: apply human-APPROVED learning cards to the KB, then open a PR.

This is the ONLY component that writes a knowledge-base file, and it is
human-run (never invoked by the weekly job). Discipline baked in:

- **Append-only.** ``write_entry`` opens both files in append mode. We never
  ``Write``/overwrite an ``@``-imported learnings file (cf. the 2026-05-08
  "Write stubbed a learnings file, lost ~120 lines" mistake).
- **Body to archive, headline+core to index.** The full body goes to
  ``<file>-archive.md`` (NOT ``@``-imported); only the ``### headline`` line and
  a one-line core go to the ``@``-imported index — keeping the always-loaded
  prefix small (the condensed-index-split). The headline is byte-identical in
  both so grep + memory-search anchor on it.
- **Routing.** ``global`` cards land in ``~/.claude/learnings`` (the dotfiles
  repo); a ``<project>`` card lands in ``~/workspace/<project>/.claude/learnings``.
  Within a tier each card is classified into one of the four files
  (anti-patterns / environment / validated / mistakes).
- **Dedup.** A card whose headline strongly overlaps an existing ``### headline``
  in its target file-set is flagged a probable duplicate and skipped (the human
  PR review is the final gate).
- **PR, never direct push.** ``main()`` writes per repo, commits on a branch and
  opens a PR via ``gh``; default is a dry-run. Pass ``--apply`` to write + PR.
"""
import argparse
import html
import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path

from learnings_extractor.lib import vikunja

# Resolve the symlink (~/.claude/learnings -> ~/dotfiles/.claude/learnings) to the
# canonical in-repo path, so `git add` sees the file as inside the dotfiles repo
# (an absolute symlinked path is "outside repository" and git add fails).
GLOBAL_ROOT = os.path.realpath(os.path.expanduser("~/.claude/learnings"))
WORKSPACE = os.path.expanduser("~/workspace")
_STOP = {"a", "an", "the", "is", "to", "of", "in", "on", "for", "and", "or",
         "but", "it", "x", "y", "n", "via", "with", "by", "as"}


# ---------------------------------------------------------------- routing/format

def classify_file(card):
    """Pick the learnings base name for a card (4-way, heuristic)."""
    t = (card.get("headline", "") + " " + card.get("core", "")).lower()
    if re.search(r"\b(never|don't|do not|avoid)\b", t):
        return "anti-patterns"
    if re.search(r"\b(use |prefer |reach for|the right tool|validated approach)\b", t):
        return "validated"
    # tool/system gotchas (the bulk) and specific failures both default to
    # environment — the catch-all for "X behaves like Y" toolchain quirks.
    return "environment"


def target_files(card, global_root=GLOBAL_ROOT, workspace=WORKSPACE):
    """Return (index_path, archive_path) for a card based on routing + type."""
    routing = (card.get("routing") or "global").strip()
    base = classify_file(card)
    if routing and routing != "global":
        root = Path(workspace) / routing / ".claude" / "learnings"
    else:
        root = Path(global_root)
    return root / f"{base}.md", root / f"{base}-archive.md"


def build_headline(card, date):
    """`### <headline>` with a trailing date if the headline lacks one."""
    h = re.sub(r"^#+\s*", "", card.get("headline", "").strip())
    if not re.search(r"\d{4}-\d\d-\d\d\s*$", h):
        h = f"{h} — {date}"
    return f"### {h}"


def build_archive_body(card):
    """Full archive body: core + evidence + cross-check."""
    lines = [f"- {card.get('core', '').strip()}"]
    ev = card.get("evidence_session_ids") or []
    if ev:
        lines.append(f"- Evidence: {len(ev)} session(s) — {', '.join(ev[:8])}"
                     + (" …" if len(ev) > 8 else ""))
    cc = card.get("crosscheck") or {}
    if cc.get("verdict"):
        lines.append(f"- Cross-check (gemini): {cc['verdict']}"
                     + (f" — {cc['reason']}" if cc.get("reason") else ""))
    return "\n".join(lines)


# ----------------------------------------------------------------------- dedup

def _tokens(headline):
    h = re.sub(r"^#+\s*", "", headline)
    h = re.sub(r"\s*[—-]\s*\d{4}-\d\d-\d\d\s*$", "", h)
    return set(re.findall(r"[a-z0-9_]+", h.lower())) - _STOP


def existing_headlines(paths):
    out = []
    for p in paths:
        p = Path(p)
        if p.exists():
            out += [ln[4:].strip() for ln in p.read_text().splitlines()
                    if ln.startswith("### ")]
    return out


def is_probable_dup(headline, existing, threshold=0.5):
    """True if `headline` token-overlaps any existing headline >= threshold."""
    ht = _tokens(headline)
    if not ht:
        return False
    for e in existing:
        et = _tokens(e)
        if et and len(ht & et) / len(ht | et) >= threshold:
            return True
    return False


# ----------------------------------------------------------------- write + io

def write_entry(index_path, archive_path, headline, body, core=""):
    """Append headline(+core) to the @-imported index and the full entry to archive.

    Append-only: existing content in both files is preserved. The body never
    lands in the @-imported index.
    """
    index_path = Path(index_path)
    archive_path = Path(archive_path)
    with index_path.open("a") as f:
        f.write(f"\n{headline}\n" + (f"- {core}\n" if core else ""))
    with archive_path.open("a") as f:
        f.write(f"\n{headline}\n{body}\n")


def _field(body, label):
    # Match up to the next tag only (NOT up to `&`) — the rendered value is
    # HTML-escaped, so apostrophes etc. appear as entities (`don&#x27;t`); a
    # `[^<&]+` class would truncate the value at the first entity.
    m = re.search(rf"<b>{label}:</b>\s*([^<]+)", body or "")
    return html.unescape(m.group(1)).strip() if m else ""


def parse_card(task):
    """Recover a candidate dict from a rendered Vikunja card."""
    body = task.get("description", "") or ""
    h = re.search(r"<h3>(.*?)</h3>", body, re.S)
    headline = (html.unescape(re.sub("<.*?>", "", h.group(1)).strip())
                if h else task.get("title", ""))
    evidence = re.findall(r"<li>(.*?)</li>", body, re.S)
    cc = re.search(r"<b>Cross-check \(gemini\):</b>\s*([^<—]+)(?:—\s*([^<]+))?", body)
    return {
        "id": task.get("id"),
        "headline": headline,
        "kind": _field(body, "Kind") or "learning",
        "routing": _field(body, "Routing") or "global",
        "core": _field(body, "Core"),
        "evidence_session_ids": [html.unescape(re.sub("<.*?>", "", e)).strip()
                                 for e in evidence],
        "crosscheck": ({"verdict": cc.group(1).strip(),
                        "reason": (cc.group(2) or "").strip()} if cc else {}),
    }


def list_approved(project_id, creds=None):
    """List Vikunja cards labeled 'approved' in the review project (paginated)."""
    base, token = creds if creds else vikunja.load_creds()
    out = []
    for page in range(1, 6):
        req = urllib.request.Request(
            f"{base}/api/v1/projects/{project_id}/tasks?per_page=50&page={page}",
            headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            tasks = json.loads(resp.read())
        if not tasks:
            break
        for t in tasks:
            labels = [lbl.get("title") for lbl in (t.get("labels") or [])]
            if "approved" in labels and not t.get("done"):
                out.append(t)
    return out


def _run(cmd, cwd=None):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=cwd)


def _repo_root(path):
    return _run(["git", "-C", str(Path(path).parent), "rev-parse",
                 "--show-toplevel"]).stdout.strip()


def plan_writes(cards, date, include_projects=False):
    """Return (writes, skipped_dups, skipped_project). Each write: dict."""
    writes, dups, proj = [], [], []
    _tier_cache = {}
    for c in cards:
        routing = (c.get("routing") or "global").strip()
        if routing != "global" and not include_projects:
            proj.append(c)
            continue
        idx, arc = target_files(c)
        # dup-check against the WHOLE tier (all 4 files + archives), since the
        # heuristic classifier may file a card under a different category than
        # where its duplicate already lives.
        root = idx.parent
        if root not in _tier_cache:
            _tier_cache[root] = existing_headlines(sorted(root.glob("*.md")))
        if is_probable_dup(build_headline(c, date), _tier_cache[root], threshold=0.45):
            dups.append(c)
            continue
        writes.append({"card": c, "index": idx, "archive": arc,
                       "headline": build_headline(c, date),
                       "core": c.get("core", ""),
                       "body": build_archive_body(c)})
    return writes, dups, proj


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project-id", type=int, required=True)
    ap.add_argument("--apply", action="store_true",
                    help="write files + open PR(s) (default: dry-run plan)")
    ap.add_argument("--include-projects", action="store_true",
                    help="also route project-tagged cards into their repos")
    ap.add_argument("--branch", default="learnings/apply-approved")
    ap.add_argument("--date", default=None, help="entry date (default: today)")
    args = ap.parse_args(argv)

    import datetime
    date = args.date or datetime.date.today().isoformat()

    cards = [parse_card(t) for t in list_approved(args.project_id)]
    if not cards:
        print("No approved cards.")
        return 0
    writes, dups, proj = plan_writes(cards, date, args.include_projects)
    print(f"approved={len(cards)} write={len(writes)} "
          f"probable-dup-skipped={len(dups)} project-deferred={len(proj)}")
    for w in writes:
        print(f"  WRITE [{Path(w['index']).name}] {w['headline'][:80]}")
    for c in dups:
        print(f"  DUP   {c['headline'][:80]}")
    for c in proj:
        print(f"  PROJ  ({c['routing']}) {c['headline'][:70]}")
    if not args.apply:
        print("\n[dry-run] re-run with --apply to write + open PR(s).")
        return 0

    # group writes by repo, write, commit, PR
    by_repo = {}
    for w in writes:
        write_entry(w["index"], w["archive"], w["headline"], w["body"], w["core"])
        by_repo.setdefault(_repo_root(w["index"]), []).append(w)
    for repo, ws in by_repo.items():
        _run(["git", "checkout", "-b", args.branch], cwd=repo)
        # stage only the learnings files we touched (never -A — don't sweep
        # unrelated working-tree changes into the PR)
        files = sorted({str(w["index"]) for w in ws} | {str(w["archive"]) for w in ws})
        _run(["git", "add"] + files, cwd=repo)
        _run(["git", "commit", "-m",
              f"learnings: apply {len(ws)} approved candidate(s) from #1847 backfill"],
             cwd=repo)
        _run(["git", "push", "-u", "origin", args.branch], cwd=repo)
        _run(["gh", "pr", "create", "--fill"], cwd=repo)
        print(f"opened PR in {repo} ({len(ws)} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
