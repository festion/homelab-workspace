# Migration Plan — Split `festion/mcp-servers` → `mcp-servers` + `homelab-workspace`

**Date:** 2026-06-26
**Status:** Phase 0 COMPLETE (read-only). No GitHub/destructive steps execute without explicit go-ahead.
**Recovery anchor:** `festion/mcp-servers` HEAD = `61b80e14` (pre-migration).
**Worktree:** `/home/dev/.worktrees/homelab-workspace-split` (branch `chore/homelab-workspace-split`).

---

## 1. Objective

Untangle the repo rooted at `/home/dev/workspace` (`festion/mcp-servers`), which mashes together three unrelated things:

| Today — inside `festion/mcp-servers` (root `/home/dev/workspace`, 452 tracked files) | Target |
|---|---|
| `mcp-servers/` subfolder — custom MCP server sources | → **`festion/mcp-servers`**, root at `/home/dev/workspace/mcp-servers/` (history preserved) |
| Stale gitops-auditor app (dashboard/api/output/frontend + gitops scripts/workflows) | → **DELETED** — stale fork of `festion/homelab-gitops` (canonical + only one deployed) |
| Container role + shared tooling + ~25 nested project clones | → **`festion/homelab-workspace`**, root stays at `/home/dev/workspace/` |

## 2. Phase 0 results (the reviewable manifest)

Built by intersecting the root's 452 tracked files with `homelab-gitops` (shared = the fork), then splitting the shared set into the *deployed app* vs *shared tooling*.

| Bucket | Files | Disposition |
|---|---|---|
| **EXTRACT** (`mcp-servers/`) | 76 | → new `festion/mcp-servers` (full list: `…manifest-EXTRACT.txt`) |
| **DELETE** (deployed gitops app) | **110** | dashboard 79, api 19, gitops scripts 6, gitops workflows 3, output 2, frontend 1 (full list: `…manifest-DELETE.txt`) |
| **STAYS** (container) | ~266 | 121 container-specific (`docs/`, `.claude/`, `.serena/`, `.beads/`) + 145 shared tooling |

**Key Phase-0 findings:**
- The DELETE set is cleanly bounded to **110 files** (the deployed app), NOT all 255 shared files. The "shared with homelab-gitops" set also contains dev tooling the container keeps.
- Of the 110 deployed-app files, **79 are byte-identical** to homelab-gitops and **31 drifted** — and the drift is entirely root's dependency-bump edits (no unique features). Confirms it's a stale copy.
- **Some shared tooling is LIVE and must stay:** e.g. `wrappers/gmail-manage.sh` backs the running `gmail_manage` MCP server in `~/.claude.json`. So tooling stays; only the deployed app is deleted.

## 3. Evidence this is safe

- `mcp-servers/` is live: `proxmox-mcp` + `truenas` run *directly* from `/home/dev/workspace/mcp-servers/...` (paths in `~/.claude.json`). These paths MUST NOT change.
- Root dashboard is a stale fork of `homelab-gitops` (shared lineage, diverged 2025-04-17; homelab-gitops is fuller + actively developed).
- Root dashboard is deployed NOWHERE: root `deploy.yml` only builds an orphan tarball. The live dashboard (CT 123 / `192.168.1.136` / `gitops-audit-api`, `/opt/gitops`, not a git checkout) is deployed solely by `homelab-gitops`.

## 4. Invariants / hard constraints

1. **Never delete the working files under `mcp-servers/`** — `git rm --cached` only. Live servers read files, not git.
2. **No secrets into the new repo's history** — scan the extracted history (gitleaks/trufflehog) before any push. Live `proxmox_mcp_config.json` is gitignored (good); tracked configs are `.example`/templates (verify).
3. **GitHub rename/create are Mode-3** — explicit confirmation each. The `festion/mcp-servers` name pivots: root must vacate (rename → `homelab-workspace`) before the extraction claims it.
4. **`homelab-gitops` untouched** — only the root's stale copy is deleted.

## 5. Phased migration

- **Phase 0 — Pre-flight (DONE):** manifest above, recovery anchor `61b80e14`, drift confirmed (79 identical / 31 dep-drift), worktree provisioned.
- **Phase 1 — Extract** `mcp-servers/` with history (`git filter-repo --subdirectory-filter mcp-servers` in a scratch clone) → **secret-scan** the rewrite → ensure `.gitignore` covers `.venv/`/`node_modules/`/real `*_config.json`. Hold locally.
- **Phase 2 — Rename** `festion/mcp-servers` → `festion/homelab-workspace` (Mode-3); GitHub redirect; `git remote set-url`. Name now free.
- **Phase 3 — Create** `festion/mcp-servers` (Mode-3), push the extraction.
- **Phase 4 — Slim container** (this worktree → PR): `git rm -r --cached mcp-servers/` (files stay); `git rm -r` the 110 DELETE-app files; fix CI (`security-scan`/`lint-and-test` audited the deleted dashboard) + branch-protection (PR #54) + `dependabot-auto-merge.yml` repo ref; gitignore `mcp-servers/`; update README/CLAUDE.md.
- **Phase 5 — Re-home** `mcp-servers/` as an independent clone *at the same path* (`git init` + remote + fetch + `checkout -f`); gitignored runtime bits (`.venv/`, configs) stay untracked.
- **Phase 6 — Verify:** container `git status` clean; `ws-status` shows `mcp-servers` independent; **restart Claude Code** → confirm `proxmox-mcp`/`truenas` load; homelab-gitops + its deployment untouched; container CI green.

## 6. Risk & rollback

| Risk | Mitigation |
|---|---|
| Deleting dashboard loses code | Not deployed + stale fork + canonical in homelab-gitops; recoverable from `61b80e14` + history |
| Breaking live MCP servers | `--cached` only; files never move; `~/.claude.json` paths unchanged; re-clone in place |
| Secret leak into new repo history | gitleaks/trufflehog before push; scrub if needed |
| Name churn breaks refs | GitHub redirect; one in-repo ref (`dependabot-auto-merge.yml`) updated |
| Wrong-branch commit | All container commits via this worktree + PR |

## 7. Decisions recorded

- Subfolder takes the `festion/mcp-servers` name; container is `festion/homelab-workspace`.
- Root dashboard is **deleted** (not moved); nested projects use the **ignored-clone** model (PR #55).
- **Shared tooling stays** in the container (some is live); only the 110-file deployed app is deleted.

## 8. Open items before execution

- [ ] Go-ahead for Mode-3 GitHub ops (rename + create).
- [ ] Confirm the REVIEW-tooling default (STAYS) — or flag any tooling dir to also shed (separate cleanup).
- [ ] New `festion/mcp-servers` CI/branch protection now or later (recommend later).
