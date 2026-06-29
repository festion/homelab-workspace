"""Stage 5: render surviving candidates as Vikunja approval cards.

The job's ONLY external mutation. Cards carry the proposed entry, the evidence
excerpts, and BOTH model verdicts so a human can approve/deny. A cross-check
disagreement (or an unparseable verdict, which fails safe to "disagree") flags
the title with ``[CONFLICT]`` — disagreement is a feature, not noise.

Creds come from ``~/.claude.json`` -> ``mcpServers.vikunja.env``
(``VIKUNJA_URL`` + ``VIKUNJA_API_TOKEN``), the same source ``vikunja-queue``
uses. HTTP via stdlib ``urllib`` only (no new deps). Vikunja descriptions are
raw HTML.
"""
import json
import os
import urllib.request
from html import escape
from pathlib import Path


def _verdict(candidate):
    return (candidate.get("crosscheck") or {}).get("verdict", "")


def card_title(candidate):
    headline = candidate.get("headline", "")
    title = f"[Learning] {headline}"
    if _verdict(candidate) != "agree":
        title = f"[CONFLICT] {title}"
    return title


def render_card(candidate):
    """Build the HTML card body: proposed entry + evidence + both verdicts."""
    cc = candidate.get("crosscheck") or {}
    parts = [
        f"<h3>{escape(str(candidate.get('headline', '')))}</h3>",
        f"<p><b>Kind:</b> {escape(str(candidate.get('kind', '')))} &nbsp; "
        f"<b>Routing:</b> {escape(str(candidate.get('routing', '')))}</p>",
        f"<p><b>Core:</b> {escape(str(candidate.get('core', '')))}</p>",
    ]
    if candidate.get("primary"):
        parts.append(f"<p><b>Primary draft (Opus):</b><br>"
                     f"{escape(str(candidate['primary']))}</p>")
    parts.append(
        f"<p><b>Cross-check (gemini):</b> {escape(str(cc.get('verdict', '')))}"
        + (f" — {escape(str(cc.get('reason', '')))}" if cc.get("reason") else "")
        + "</p>")
    evidence = candidate.get("evidence") or candidate.get("evidence_session_ids") or []
    if evidence:
        items = "".join(f"<li>{escape(str(e))}</li>" for e in evidence)
        parts.append(f"<p><b>Evidence sessions:</b></p><ul>{items}</ul>")
    return "\n".join(parts)


def load_creds(path="~/.claude.json"):
    data = json.loads(Path(os.path.expanduser(path)).read_text())
    env = data.get("mcpServers", {}).get("vikunja", {}).get("env", {})
    return env["VIKUNJA_URL"].rstrip("/"), env["VIKUNJA_API_TOKEN"]


def create_card(project_id, candidate, creds=None):
    """Create one approval card in the given Vikunja project. Thin live PUT.

    Vikunja creates a task via ``PUT /api/v1/projects/{id}/tasks``.
    """
    base, token = creds if creds else load_creds()
    payload = json.dumps({
        "title": card_title(candidate),
        "description": render_card(candidate),
    }).encode()
    req = urllib.request.Request(
        f"{base}/api/v1/projects/{project_id}/tasks",
        data=payload, method="PUT",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())
