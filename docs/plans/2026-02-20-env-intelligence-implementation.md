# Environment Intelligence Skill Suite — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build four Claude Code skills (`/briefing`, `/investigate`, `/changelog`, `/trends`) that intelligently query the homelab infrastructure and synthesize actionable reports.

**Architecture:** Workspace-level skills in `.claude/skills/env-intel/` with a shared `datasources.yaml` config. Each skill is a markdown file with YAML frontmatter. Skills instruct Claude to use MCP tools (Proxmox, TrueNAS, GitHub), SSH commands, and HTTP APIs to gather data, then reason about and present findings.

**Tech Stack:** Claude Code skills (markdown + YAML frontmatter), YAML config, MCP tools, Bash (SSH, curl)

**Design doc:** `docs/plans/2026-02-20-env-intelligence-design.md`

---

## Task 1: Create Shared Data Sources Config

**Files:**
- Create: `.claude/skills/env-intel/datasources.yaml`

**Step 1: Create the directory**

```bash
mkdir -p /home/dev/workspace/.claude/skills/env-intel
```

**Step 2: Write `datasources.yaml`**

```yaml
# Environment Intelligence — Shared Data Source Configuration
# Read by all env-intel skills at invocation time.
# Update this file when infrastructure changes (new nodes, IPs, services).

compute:
  proxmox:
    tool_prefix: mcp__proxmox-mcp
    nodes:
      - name: proxmox
        ip: 192.168.1.137
        cpu_cores: 4
        role: "HA master"
      - name: proxmox2
        ip: 192.168.1.125
        cpu_cores: 8
      - name: proxmox3
        ip: 192.168.1.126
        cpu_cores: 8
    ssh_user: root

storage:
  truenas:
    tool_prefix: mcp__truenas
    ip: 192.168.1.98
  pbs:
    ip: 192.168.1.171
    port: 8007
    ssh_user: root

services:
  home_assistant:
    ip: 192.168.1.155
    port: 8123
    api_path: /api/
    token_source: "Run: cd /home/dev/workspace && infisical secrets get HA_LONG_LIVED_TOKEN --env=prod --plain"
  birdnet:
    ip: 192.168.1.197
    port: 8080
    api_path: /api/v2/
    ssh_user: jeremy
  loki:
    ip: 192.168.1.170
    port: 3100

monitoring:
  proxmox_agent:
    ct: 152
    node: proxmox2
    ip: 192.168.1.169
    port: 8000
    api_path: /api/
    auth_source: "SSH to proxmox2, pct exec 152 -- cat /opt/proxmox-agent/.env for DASHBOARD_USER and DASHBOARD_PASSWORD"

code:
  github:
    tool_prefix: mcp__github
    owner: festion
    repos:
      - mcp-servers
      - homelab-gitops
      - home-assistant-config
      - proxmox-agent
      - birdnet-gone
      - pi-status-dashboard
      - operations

thresholds:
  storage_warning_pct: 80
  storage_critical_pct: 90
  load_warning_multiplier: 2.0
  backup_max_age_hours: 36
  unavailable_entities_warning: 5
```

**Step 3: Commit**

```bash
git add .claude/skills/env-intel/datasources.yaml
git commit -m "feat(env-intel): add shared datasources config"
```

---

## Task 2: Create `/briefing` Skill

**Files:**
- Create: `.claude/skills/env-intel/briefing.md`

**Step 1: Write the skill file**

The skill file instructs Claude on what to do when `/briefing` is invoked. It's a set of instructions, not executable code — Claude interprets and follows them using its available tools.

```markdown
---
name: briefing
description: Morning environment briefing. Summarizes overnight health, events, alerts, and action items across all homelab infrastructure. Use at start of day.
---

# Environment Briefing

Generate a comprehensive morning briefing of the homelab environment. The value is in YOUR interpretation — correlate events, flag anomalies, prioritize action items. Don't just dump data.

## Reference

Read `.claude/skills/env-intel/datasources.yaml` for all endpoints, IPs, and thresholds.

## Data Gathering

Gather data from ALL sources below. Use parallel tool calls where possible.

### 1. Compute — Proxmox Cluster

Use the Proxmox MCP tools:

- `mcp__proxmox-mcp__get_system_info` — cluster version, node count, quorum
- `mcp__proxmox-mcp__list_containers` — all CTs with status (look for stopped CTs that should be running)
- `mcp__proxmox-mcp__list_virtual_machines` — all VMs with status
- `mcp__proxmox-mcp__monitor_resource_usage` — CPU, RAM, load per node

Flag: Any node down, any CT stopped with `onboot: 1`, load > threshold.

### 2. Storage — TrueNAS

Use the TrueNAS MCP tools:

- `mcp__truenas__list_pools` — pool health, usage %
- `mcp__truenas__get_system_info` — system uptime, version

Flag: Any pool degraded, usage > 80%, any SMART warnings.

### 3. Backups — PBS

SSH to proxmox (192.168.1.137) as root and run:
```bash
ssh root@192.168.1.137 "pvesh get /nodes/proxmox/tasks --typefilter vzdump --limit 20 --output-format json 2>/dev/null"
```

Parse the task list for backup jobs in the last 36 hours. Check for failures (status != "OK").

### 4. Alerts — Proxmox Agent Dashboard

Get credentials first:
```bash
ssh root@192.168.1.125 "pct exec 152 -- cat /opt/proxmox-agent/.env" 2>/dev/null
```

Extract DASHBOARD_USER and DASHBOARD_PASSWORD, then query:
```bash
ssh root@192.168.1.125 "pct exec 152 -- curl -s -u USER:PASS http://localhost:8000/api/alerts?acknowledged=false" 2>/dev/null
```

Flag: Any unacknowledged alerts, especially critical/high severity.

### 5. Home Assistant

Get the HA token:
```bash
cd /home/dev/workspace && infisical secrets get HA_LONG_LIVED_TOKEN --env=prod --plain 2>/dev/null
```

Query the HA API:
```bash
curl -s -H "Authorization: Bearer TOKEN" http://192.168.1.155:8123/api/states | python3 -c "
import json, sys
states = json.load(sys.stdin)
unavailable = [s['entity_id'] for s in states if s['state'] in ('unavailable', 'unknown')]
print(json.dumps({'total': len(states), 'unavailable_count': len(unavailable), 'unavailable': unavailable[:20]}))"
```

Flag: Entity count > threshold, any critical entities unavailable.

### 6. BirdNET-Go

```bash
curl -s "http://192.168.1.197:8080/api/v2/detections?limit=100" 2>/dev/null
```

Report: Detection count in last 24h, species diversity, any notable detections (rare species, high confidence).

### 7. GitHub — Dependabot & CI

Use GitHub MCP tools for each repo in the config:

- `mcp__github__list_issues` with `labels: ["dependencies"]` for Dependabot alerts
- Check for recent failed CI runs (optional — skip if rate-limited)

Flag: Any open security alerts.

## Output Format

Present as a clean markdown briefing:

```
## Environment Briefing — {today's date}

### Health: {emoji} {status}
| System | Status | Notes |
|--------|--------|-------|
| ... one row per system ... |

### Overnight Events
- **HH:MM** Notable events with context (skip if nothing notable)

### Action Items
- [ ] Items requiring human attention, ordered by priority

### Quick Stats
- Key numbers: detections, load averages, alert counts, etc.
```

## Intelligence Rules

1. **Correlate:** If backup ran at 01:00 and load spiked at 01:00 — that's expected, don't flag it
2. **Threshold:** Use thresholds from datasources.yaml to determine warning/critical
3. **Known issues:** Check MEMORY.md and learnings files for known patterns (Sunday 3AM = Ultimate Updater)
4. **Omit noise:** If a system is fully healthy, just show ✅ in the health table — no need for details
5. **Prioritize:** Action items ordered: critical > high > medium > informational
6. **Be concise:** This is a morning scan. Details go in `/investigate`.
```

**Step 2: Verify the skill is discovered**

The skill should appear in Claude Code's skill list automatically since it's in `.claude/skills/`. Verify by checking that the frontmatter `name: briefing` is correctly formatted.

**Step 3: Commit**

```bash
git add .claude/skills/env-intel/briefing.md
git commit -m "feat(env-intel): add /briefing morning environment skill"
```

---

## Task 3: Create `/investigate` Skill

**Files:**
- Create: `.claude/skills/env-intel/investigate.md`

**Step 1: Write the skill file**

```markdown
---
name: investigate
description: Deep-dive investigation into a specific system or anomaly. Use when something looks off or you want detailed diagnostics. Pass target as argument, e.g., /investigate proxmox2
---

# Environment Investigation

Deep-dive into a specific system. The ARGUMENTS string contains the target to investigate.

## Reference

Read `.claude/skills/env-intel/datasources.yaml` for all endpoints, IPs, and thresholds.
Read MEMORY.md and relevant learnings files for known issues with the target system.

## Target Routing

Parse the ARGUMENTS to determine the target. Route to the appropriate diagnostic section below.

### Proxmox Node: `proxmox`, `proxmox2`, `proxmox3`

1. **Node details:** `mcp__proxmox-mcp__get_node_status` for the specific node
2. **Container breakdown:** `mcp__proxmox-mcp__list_containers` filtered to that node — show per-CT CPU/RAM
3. **Resource monitoring:** `mcp__proxmox-mcp__monitor_resource_usage` for the node
4. **ZFS status:** SSH to node: `zpool status && zpool list && arc_summary 2>/dev/null | head -30`
5. **Recent logs:** SSH: `journalctl --since '24 hours ago' -p err --no-pager | tail -50`
6. **Cron status:** SSH: `systemctl status cron` (known to die silently — see MEMORY.md gotcha #1)
7. **HA services:** SSH: `ha-manager status 2>/dev/null`
8. **Disk I/O:** SSH: `iostat -x 1 3 2>/dev/null || echo "iostat not available"`

Analyze: Compare load to CPU core count. Check if any CT is consuming disproportionate resources. Look for ZFS ARC pressure. Check if cron is running.

### TrueNAS: `truenas`, `nas`, `storage`

1. **System info:** `mcp__truenas__get_system_info`
2. **Pool details:** `mcp__truenas__list_pools` then `mcp__truenas__get_pool_status` for each pool
3. **Dataset usage:** `mcp__truenas__list_datasets` — sort by usage, flag large datasets
4. **SMB shares:** `mcp__truenas__list_smb_shares`

Analyze: Check pool health, capacity trends, any degraded vdevs, scrub status.

### Backups: `backups`, `pbs`, `backup`

1. **Recent backup tasks:** SSH to proxmox: `pvesh get /nodes/proxmox/tasks --typefilter vzdump --limit 50 --output-format json`
2. **PBS status:** SSH to PBS (192.168.1.171): `proxmox-backup-manager datastore list 2>/dev/null`
3. **Storage usage:** `mcp__proxmox-mcp__get_storage_status`

Analyze: Check for failed backups, duration anomalies, storage growth rate.

### Home Assistant: `ha`, `home-assistant`, `homeassistant`

1. **Get token** from Infisical (see briefing skill for command)
2. **All states:** Query `/api/states` — categorize unavailable entities by domain
3. **Error log:** Query `/api/error/all` or `/api/error_log`
4. **Service status:** Check if HA API responds, response time
5. **Automation failures:** Query for failed automations in last 24h

Analyze: Group unavailable entities by integration. Check if a single integration is down vs. scattered failures.

### BirdNET: `birdnet`, `birdnet-go`, `birds`

1. **Recent detections:** `curl http://192.168.1.197:8080/api/v2/detections?limit=200`
2. **Service status:** SSH to BirdNET Pi: `systemctl status birdnet-go-native.service`
3. **Disk usage:** SSH: `df -h /home/jeremy/`
4. **Audio source:** SSH: `arecord -l 2>/dev/null` to verify USB mic connected
5. **MQTT connectivity:** SSH: `mosquitto_pub -h 192.168.1.149 -t test -m test 2>&1`

Analyze: Check detection rate, audio source health, disk space, MQTT broker reachability.

### Loki: `loki`, `logs`

1. **Health:** `curl -s http://192.168.1.170:3100/ready`
2. **Ingestion rate:** `curl -s 'http://192.168.1.170:3100/loki/api/v1/query?query=sum(rate({job=~".%2B"}[1h]))'`
3. **Active jobs:** `curl -s 'http://192.168.1.170:3100/loki/api/v1/labels' | python3 -c "import json,sys; print(json.dumps(json.load(sys.stdin),indent=2))"`
4. **Disk usage:** SSH to proxmox2: `pct exec 151 -- df -h /var/lib/loki`

Analyze: Check for missing log sources (compare active jobs to expected list of ~41), ingestion anomalies.

### Container by Name or ID: `<container-name>` or `<CTID>`

1. **Find the CT:** `mcp__proxmox-mcp__list_containers` — match by name or VMID
2. **CT config:** SSH to node: `pct config CTID`
3. **CT status:** `mcp__proxmox-mcp__list_containers` filtered
4. **Recent logs:** SSH to node: `pct exec CTID -- journalctl --since '24 hours ago' -p err --no-pager 2>/dev/null | tail -30`
5. **Service status:** SSH: `pct exec CTID -- systemctl list-units --state=failed 2>/dev/null`
6. **Resource usage:** SSH: `pct exec CTID -- free -m && pct exec CTID -- df -h /`

Analyze: Check for failed services, resource exhaustion, error logs.

## Output Format

```
## Investigation: {target}

### Summary
One paragraph: Is it healthy? What stands out?

### Diagnostics
Detailed findings organized by category.

### Known Issues
Cross-reference with learnings/MEMORY.md — any known gotchas for this system?

### Recommendations
Specific actions if any issues found. Reference remediation procedures from learnings.
```
```

**Step 2: Commit**

```bash
git add .claude/skills/env-intel/investigate.md
git commit -m "feat(env-intel): add /investigate deep-dive skill"
```

---

## Task 4: Create `/changelog` Skill

**Files:**
- Create: `.claude/skills/env-intel/changelog.md`

**Step 1: Write the skill file**

```markdown
---
name: changelog
description: Audit what changed in the environment over a time window. Shows code commits, package updates, container changes, alerts. Default 24h. Usage /changelog or /changelog 48h or /changelog week
---

# Environment Changelog

Show what changed in the environment over a time window. ARGUMENTS contains the timeframe (default: "24h"). Parse it to determine the lookback period.

## Reference

Read `.claude/skills/env-intel/datasources.yaml` for repos, nodes, and endpoints.

## Timeframe Parsing

- No argument or "24h" → last 24 hours
- "48h" → last 48 hours
- "week" or "7d" → last 7 days
- Any other number+h/d → that duration

Calculate the `--since` date for git and the start timestamp for API queries.

## Data Gathering

### 1. Code Changes — GitHub

For each repo in `datasources.yaml`:

```bash
mcp__github__list_commits owner=festion repo=REPO_NAME
```

Filter commits within the timeframe. Show: date, author, message, files changed count.

### 2. Package Updates — Proxmox Nodes

For each node, SSH and check dpkg log:

```bash
ssh root@NODE_IP "grep -E 'install|upgrade|remove' /var/log/dpkg.log 2>/dev/null | tail -30"
```

And apt history:

```bash
ssh root@NODE_IP "grep -A2 'Start-Date:' /var/log/apt/history.log 2>/dev/null | tail -30"
```

### 3. Container Changes — Proxmox

Use `mcp__proxmox-mcp__list_containers` and `mcp__proxmox-mcp__list_virtual_machines`.

Compare against the known container list in MEMORY.md — flag any new or missing CTs.

### 4. Alert History — Proxmox Agent

Get dashboard API credentials (see briefing skill), then:

```bash
ssh root@192.168.1.125 "pct exec 152 -- curl -s -u USER:PASS 'http://localhost:8000/api/alerts?limit=100'" 2>/dev/null
```

Filter alerts within timeframe.

### 5. TrueNAS Changes

```bash
mcp__truenas__list_datasets
```

Note any new datasets or shares. Check TrueNAS audit log if available via SSH.

### 6. Home Assistant Changes

Check the home-assistant-config repo commits (covered by GitHub section above). Also check for any HA restarts in the period via Loki:

```bash
curl -sG 'http://192.168.1.170:3100/loki/api/v1/query_range' \
  --data-urlencode 'query={job="home-assistant"} |= "started"' \
  --data-urlencode "start=$(date -d 'TIMEFRAME ago' +%s)000000000" \
  --data-urlencode "end=$(date +%s)000000000" \
  --data-urlencode 'limit=20'
```

## Output Format

```
## Environment Changelog — {timeframe}

### Code Changes
| Repo | Commits | Summary |
|------|---------|---------|
| ... | N | Brief description of changes |

Details:
- **repo** `abc1234` — commit message (author, date)

### Infrastructure Changes
- Package updates on nodes (if any)
- Container additions/removals (if any)
- TrueNAS dataset changes (if any)

### Alert Timeline
- **HH:MM** Alert description (severity)

### Service Events
- HA restarts, BirdNET restarts, etc.
```

## Intelligence Rules

1. **Risk assessment:** For each change, note if it's routine (Dependabot bump), notable (config change), or requires attention (failed deployment)
2. **Correlation:** If a service restarted and alerts fired around the same time, connect them
3. **Omit empty sections:** If no package updates happened, skip that section entirely
```

**Step 2: Commit**

```bash
git add .claude/skills/env-intel/changelog.md
git commit -m "feat(env-intel): add /changelog change audit skill"
```

---

## Task 5: Create `/trends` Skill

**Files:**
- Create: `.claude/skills/env-intel/trends.md`

**Step 1: Write the skill file**

```markdown
---
name: trends
description: Analyze trends in storage, backups, alerts, and compute over time. Provides capacity projections and identifies recurring patterns. Usage /trends or /trends storage or /trends backups
---

# Environment Trend Analysis

Analyze trends and project capacity. ARGUMENTS contains the optional system focus (default: all systems).

## Reference

Read `.claude/skills/env-intel/datasources.yaml` for endpoints and thresholds.

## System Routing

- No argument or "all" → analyze all systems
- "storage" → TrueNAS + PBS storage trends
- "backups" → backup duration and size trends
- "alerts" → alert frequency and patterns
- "compute" → CPU, RAM, load trends

## Data Gathering

### Storage Trends

1. **TrueNAS pools:** `mcp__truenas__list_pools` — current usage
2. **TrueNAS datasets:** `mcp__truenas__list_datasets` — per-dataset sizes
3. **PBS datastore:** SSH to proxmox: `pvesh get /storage --output-format json` — check PBS storage usage
4. **Proxmox local storage:** `mcp__proxmox-mcp__get_storage_status` for each node

For projections: If historical data is not available from a single query, note the current values and suggest the user run `/trends storage` periodically to build a baseline. With multiple data points over time, calculate growth rates.

### Backup Trends

1. **Recent backup tasks:** SSH to proxmox: `pvesh get /nodes/proxmox/tasks --typefilter vzdump --limit 100 --output-format json`
2. Parse: Extract start time, end time (duration), and data size per backup
3. Calculate: Average duration, duration trend (getting longer?), total backup size trend

### Alert Trends

1. **Full alert history:** Query proxmox-agent dashboard API (get auth, then fetch all alerts)
2. Categorize: By severity, by type, by time of day
3. Identify: Recurring patterns (same alert type at same time = systemic), frequency changes

### Compute Trends

1. **Current resource usage:** `mcp__proxmox-mcp__monitor_resource_usage` for all nodes
2. **Historical context:** Note that real-time monitoring gives a snapshot. For trends, compare current values against known baselines from MEMORY.md (e.g., "load was 1.0-2.2 on proxmox after thundering herd fix")
3. **Per-CT resource usage:** `mcp__proxmox-mcp__list_containers` with resource details

## Output Format

```
## Trend Analysis — {date}

### Storage
| Location | Current | Capacity | Projection |
|----------|---------|----------|------------|
| TrueNAS main pool | 78% | 10 TB | ~45 days to 90% (if growth continues) |
| PBS datastore | ... | ... | ... |
| proxmox local-lvm | ... | ... | ... |

### Backups
- Average backup duration: Xm (last 7d)
- Total backup size: X GB
- Trend: {stable/growing/shrinking}

### Alerts
- Total alerts (7d): N
- By severity: critical: X, high: Y, medium: Z
- Recurring patterns: {description}

### Compute
| Node | CPU Avg | RAM % | Load | Headroom |
|------|---------|-------|------|----------|
| proxmox | X% | Y% | Z | {plenty/moderate/tight} |

### Recommendations
- Prioritized list of capacity or reliability actions
```

## Intelligence Rules

1. **Don't fabricate trends:** If you only have a single data point, say so. "Current usage is 78% — run `/trends storage` weekly to track growth rate."
2. **Known patterns:** Sunday 3 AM load spikes = Ultimate Updater (expected). Daily 01:00 = backup window (expected). Don't flag these as anomalies.
3. **Actionable projections:** "Pool hits 90% in ~45 days" is useful. "CPU was 12% today" without context is not.
4. **Compare to thresholds:** Use thresholds from datasources.yaml.
```

**Step 2: Commit**

```bash
git add .claude/skills/env-intel/trends.md
git commit -m "feat(env-intel): add /trends capacity analysis skill"
```

---

## Task 6: Test and Validate All Skills

**Step 1: Verify file structure**

```bash
ls -la /home/dev/workspace/.claude/skills/env-intel/
```

Expected: `datasources.yaml`, `briefing.md`, `investigate.md`, `changelog.md`, `trends.md`

**Step 2: Verify YAML frontmatter is valid**

For each `.md` file, confirm the frontmatter has `name` and `description` fields between `---` delimiters.

```bash
for f in /home/dev/workspace/.claude/skills/env-intel/*.md; do
  echo "=== $(basename $f) ==="
  head -4 "$f"
  echo
done
```

**Step 3: Smoke test `/briefing`**

Invoke `/briefing` in a new Claude Code conversation. Verify:
- It reads `datasources.yaml`
- It queries Proxmox MCP, TrueNAS MCP, GitHub MCP in parallel
- It attempts SSH commands for PBS, alerts, HA, BirdNET
- Output follows the briefing format from the design

**Step 4: Smoke test `/investigate proxmox2`**

Invoke `/investigate proxmox2`. Verify:
- It routes to the Proxmox node diagnostics section
- It queries node-specific data
- Output includes per-CT breakdown, ZFS status, cron check

**Step 5: Final commit with all files**

If any adjustments were needed during testing, commit them:

```bash
git add .claude/skills/env-intel/
git commit -m "feat(env-intel): environment intelligence skill suite complete

Four Claude Code skills for intelligent infrastructure monitoring:
- /briefing: morning environment summary
- /investigate: deep-dive diagnostics
- /changelog: change audit with timeline
- /trends: capacity projections and patterns

Includes shared datasources.yaml config."
```

Then push:

```bash
git pushx
```
