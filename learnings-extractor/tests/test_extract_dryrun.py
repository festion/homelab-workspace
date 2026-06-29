"""Hermetic smoke test for the integration wrapper.

Stubs claude/gemini/memory-search on PATH (no network, no live index, no LLM)
so `bash extract.sh --dry-run` runs end-to-end and prints a card without
creating anything in Vikunja or touching a KB file.
"""
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent  # learnings-extractor/ project root


def _stub(bindir, name, body):
    p = bindir / name
    p.write_text("#!/usr/bin/env bash\n" + body + "\n")
    p.chmod(0o755)


def test_dry_run_prints_card_and_exits_zero(tmp_path):
    # 1) a transcript dir with one planted friction window
    tdir = tmp_path / "transcripts"
    tdir.mkdir()
    line = lambda r, t: json.dumps({"type": r, "message": {"role": r, "content": t}})
    (tdir / "sess.jsonl").write_text(
        "\n".join([line("user", "do X"), line("assistant", "done"),
                   line("user", "no that's wrong")]) + "\n")

    # 2) stub the three external CLIs
    bindir = tmp_path / "bin"
    bindir.mkdir()
    candidate = [{"kind": "learning", "headline": "Stub pattern", "core": "c",
                  "routing": "global", "evidence_session_ids": ["sess"],
                  "occurrence_count": 2}]
    _stub(bindir, "claude", f"cat <<'EOF'\n{json.dumps(candidate)}\nEOF")
    _stub(bindir, "gemini", 'cat <<\'EOF\'\n{"verdict":"agree","reason":"ok"}\nEOF')
    _stub(bindir, "memory-search", "echo '[]'")  # novel -> kept

    env = dict(os.environ, PATH=f"{bindir}:{os.environ['PATH']}")
    state = tmp_path / "state.json"
    r = subprocess.run(
        ["bash", str(ROOT / "extract.sh"), "--dry-run",
         "--transcripts", str(tdir), "--state", str(state),
         "--since", "7d", "--project-id", "1"],
        capture_output=True, text=True, env=env, timeout=120)

    assert r.returncode == 0, r.stderr
    assert "Stub pattern" in r.stdout  # the card was printed, not POSTed
