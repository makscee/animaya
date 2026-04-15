# Roadmap: Animaya v2

## Overview

Animaya v2 is a modular AI assistant platform for Claude Boxes (LXC + Claude Code). Users get a Telegram bridge, web dashboard, and an installable module system.

## Milestones

<details>
<summary><strong>v1.0 — Audit Gaps</strong> (shipped 2026-04-15, 7 phases, 29 plans, 27/27 REQ satisfied)</summary>

| Phase | Name | Status |
|-------|------|--------|
| 1 | Install & Foundation | Complete 2026-04-13 |
| 2 | Telegram Bridge | Complete 2026-04-13 |
| 3 | Module System | Complete 2026-04-14 |
| 4 | First-Party Modules | Complete 2026-04-14 |
| 5 | Web Dashboard | Complete 2026-04-15 |
| 6 | Telethon Test Harness | Complete 2026-04-14 |
| 7 | Close v1.0 Audit Gaps | Complete 2026-04-15 |

Audit: `tech_debt` — all requirements satisfied; Nyquist partial on phases 01/03/05 (non-blocking); streaming double-bubble deferred.

Archive: `.planning/milestones/` — ROADMAP, REQUIREMENTS, AUDIT, and all 7 phase directories.

</details>

## Next Milestone

(Not yet planned — use `/gsd-new-milestone` to start v2.0 planning)

## Backlog

### Phase 999.1: Telegram bridge as installable module with owner-claim flow (BACKLOG)

**Goal:** Extract the Telegram bridge from core into an installable module. Install flow accepts bot token via dashboard form, starts polling only after install, stores token in config.json. Core bot starts dashboard only. First message to a freshly-installed bridge triggers an ownership-claim: bot DMs a 6-digit code shown on dashboard; user replies with code in Telegram to claim ownership. On claim, persist `user_id` to module config as the owner allowlist (replacing the hotfix `TELEGRAM_OWNER_ID` env gate in commit 992332f).

**Why:** Matches v2 architecture intent — "every feature beyond core must be a module." Closes the bridge-management gap (token / polling currently require restart + env edit) and lets owners rotate tokens or transfer ownership from the dashboard.

**Requirements:** TBD
**Plans:** 0 plans

Plans:
- [ ] TBD (promote with /gsd-review-backlog when ready)

