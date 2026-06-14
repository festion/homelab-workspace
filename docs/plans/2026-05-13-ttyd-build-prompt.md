# Build: ttyd web-terminal on CT 128, wired into Pushover hook

## Goal

A writable web terminal at `https://ttyd.internal.lakehouse.wtf` that auto-attaches to the long-lived tmux session `operations` on CT 128. The URL gets wired into my existing Pushover notification hook so I can tap a phone notification and land at the prompt.

## Locked decisions — do not re-litigate

- **Co-locate on CT 128** (`developmentenvironment`, 192.168.1.239, currently on proxmox3). No new LXC.
- **Auth**: ttyd built-in basic auth (`-c user:pass`). Authelia is removed. Credential stored at `homelab-gitops/prod/TTYD_BASIC_AUTH` in Infisical as a single `user:password` string. **The agent generates this in Phase 3** — it does not pre-exist.
- **Persistence**: tmux session `operations` lives on CT 128. ttyd wraps `tmux new -A -s operations`.
- **Internal-only**: no Cloudflare tunnel route. Phone reaches via home WiFi or Tailscale.
- **Hostname**: `ttyd.internal.lakehouse.wtf` (Traefik wildcard cert path).
- **Service user**: `dev` (owns the tmux socket for `operations` — verify before committing).
- **Backend port**: 7681 (ttyd default), bound to `127.0.0.1`.

## Phase 1 — Parallel research/draft (no deploys, no secret generation)

Invoke `superpowers:dispatching-parallel-agents`. In a single message, spawn the four agents below as `general-purpose` with `model: "sonnet"`. Each returns drafts only — no file writes outside its own scratch, no service installs, no API mutations, no secret generation.

Cap each agent's response to ≤200 words of commentary plus the artifact(s) requested.

**Agent A — ttyd install + systemd unit**
- Decide install path (apt on the Debian/Ubuntu CT 128 vs upstream release binary). Verify what's actually available on the container.
- Verify which UID owns `/tmp/tmux-*/default` for the live `operations` session on CT 128 — confirm `dev` is correct.
- Pick the username portion of basic-auth (e.g. `claude`) and document it in the unit's draft comments; the password is generated in Phase 3.
- Deliverable: install commands + **complete systemd unit file** running as `dev`, binding `127.0.0.1:7681`, wrapping `tmux new -A -s operations`, consuming basic-auth via `EnvironmentFile=` rendered from Infisical at deploy time (no plaintext in the unit). `Restart=on-failure`.

**Agent B — Traefik dynamic config**
- Locate `LXC-DEPLOY-TRAEFIK-LOOP-ANCHOR` in homelab-iac `roles/traefik/tasks/main.yml`.
- Pick an existing internal-only service file as the structural template (name it).
- Deliverable: **complete new dynamic-config file** for ttyd with HTTPS via wildcard cert and **WebSocket-aware** routing, plus the exact one-line append to the deploy loop. Backend: `http://192.168.1.239:7681`.

**Agent C — AdGuard rewrites**
- Deliverable: AdGuard rewrite entry for `ttyd.internal.lakehouse.wtf → 192.168.1.110` and the curl-based procedure to apply it on **both** CT 116 (192.168.1.224) and CT 1250 (192.168.1.253) via the AdGuard REST API. Use direct curl from the dev env, not SSH/pct exec (see memory `feedback_adguard_api_direct`).

**Agent D — Pushover hook + observability**
- Read `~/dotfiles/.claude/hooks/notify-pushover.sh`. Deliverable: **complete updated file** adding `url=https://ttyd.internal.lakehouse.wtf` and `url_title=Open terminal` to the curl POST. Keep the existing `attach: tmux a -t ${project}` body line.
- Deliverable: Uptime Kuma monitor spec for the HTTPS endpoint (Python API; account for Kuma 2.x `conditions` workaround per `feedback_uptime_kuma_has_api`).
- Deliverable: Homepage tile YAML for the right category — read the existing Homepage config to pick where it goes.

## Phase 2 — Aggregate + gate

After all four return, present a single consolidated summary:
- Every artifact in full (complete files, not fragments).
- Deploy order: generate Infisical secret → ttyd unit on CT 128 → local curl smoke → AdGuard rewrites → Traefik route → end-to-end WS smoke → hook change → Kuma + Homepage.
- Risks discovered that diverge from the plan above.
- **Wait for explicit "go" before any deploy.** Do not proceed on implicit approval.

If any agent returns a fragment, guess, or "I'll figure it out at deploy time," re-spawn it with the specific gap called out.

## Phase 3 — Sequential deploy (only after go)

1. **Generate and store the basic-auth credential.** Use a single command that never prints the value:
   ```bash
   USER=claude  # or whatever Agent A picked
   PASS=$(openssl rand -base64 24 | tr -d '/+=' | head -c 28)
   printf '%s:%s' "$USER" "$PASS" | infisical secrets set TTYD_BASIC_AUTH="$(cat)" --env=prod --path=/ >/dev/null 2>&1
   unset PASS
   ```
   Adapt to whatever `infisical secrets set` syntax the dev env's wrapper expects. Verify by length-only readback:
   ```bash
   infisical secrets get TTYD_BASIC_AUTH --env=prod --plain | wc -c
   ```
   Do not echo the value to chat. Do not store it in a variable that persists.

2. Render the EnvironmentFile from Infisical, install ttyd, drop the unit, `daemon-reload`, enable+start.
3. `curl -u "$(infisical secrets get TTYD_BASIC_AUTH --env=prod --plain)" http://127.0.0.1:7681/` from CT 128 returns ttyd HTML. Pipe the curl through `head -c 200` or just check rc — do not echo the auth header.
4. Apply AdGuard rewrites on both replicas.
5. Add Traefik dynamic config + loop entry; let homelab-iac reconcile apply.
6. WS handshake confirmed end-to-end (`wscat` against `wss://ttyd.internal.lakehouse.wtf/ws`, or browser devtools — not just HTTP 200).
7. Ship the updated `notify-pushover.sh` to dotfiles. Fire a synthetic Pushover by piping a test JSON payload into the deployed hook; verify the action button renders on Android.
8. From phone: tap → writable `operations` prompt → close browser → re-tap → same session, no reset.
9. Add Kuma monitor + Homepage tile.
10. Commit + push affected repos (dotfiles, homelab-iac). Confirm `changed=0` on a fresh reconcile before declaring done.

## Constraints — non-negotiable

- **The basic-auth value is never echoed, logged, or transcribed.** Pipe `infisical secrets set` to `/dev/null`; never `--diff` the rendered unit or EnvironmentFile; never paste the value into Vikunja, commits, or messages; never `cat` the file in chat. Verify writes by length/hash, not by reading back. See `learnings/anti-patterns.md` entries on Infisical CLI stdout leaks, ansible `--diff` template leaks, and `mistakes.md` entry on curl `-v` against auth endpoints.
- If at any point the value ends up in a shell variable, the transcript, or a file you can `cat`, **stop and rotate it** — generate a new one and re-store. Do not try to "delete the transcript."
- Don't invent infrastructure not specified above — ask.
- All file edits use complete files in chat, not fragments.
- Capture any side-issues to Vikunja immediately (`feedback_capture_discovered_issues`).
- The single highest-risk technical thing is WebSocket-through-Traefik. The single highest-risk security thing is the basic-auth secret. Verify both, don't assume either.
