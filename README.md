# homelab-workspace

The container repository for the Lakehouse homelab development workspace
(`/home/dev/workspace`). It tracks workspace-level tooling, docs, scripts, and
config — **not** the individual projects.

Each sub-project nested in this directory (operations, homelab-iac, homelab-gitops,
mcp-servers, tender, …) is an **independent git repository**, cloned in place and
listed in `.gitignore` under "Workspace cloned repos". This repo neither tracks
nor builds them.

## History

This repo was previously named `festion/mcp-servers`. On 2026-06-26 it was split:

- The custom MCP server sources moved to their own repo, **`festion/mcp-servers`**
  (now nested at `./mcp-servers/`, history preserved).
- A stale fork of the GitOps-auditor dashboard was removed — the canonical,
  deployed version lives in **`festion/homelab-gitops`** (also nested here).
- The remainder was renamed **`festion/homelab-workspace`** (this repo).

See `docs/plans/2026-06-26-mcp-servers-split-and-homelab-workspace-migration.md`.

## Working in here

A bare `git` command at the workspace root operates on **this** container repo.
To act on a nested project, `cd` into it (or use `git -C <project>`). Run
`ws-status` to sweep every nested repo and report which need attention.
