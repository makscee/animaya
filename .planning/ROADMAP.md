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

## Current Milestone: v2.0 — Onboarding Polish & Bridge-as-Module

**Goal:** Complete the first-run experience. Telegram bridge becomes an installable module with dashboard onboarding (token + pairing-code owner-claim); bridge gains runtime settings (master disable, non-owner policy, tool-use display); identity module pre-installed with raw-markdown editor; dashboard gains unified streaming chat + read-only Hub file tree.

**Scope:** 21 requirements across 6 categories (BRDG, CLAIM, ACC, TUI, IDN, DASH, SEC) distributed over 5 phases (8–12). Phase numbering continues from v1.0 — no reset.

### Phases

- [ ] **Phase 8: Bridge Extraction & Supervisor Cutover** — Move Telegram bridge into a first-class runtime module with supervisor-dispatched lifecycle hooks
- [ ] **Phase 9: Install Dialog & Owner-Claim FSM** — Dashboard token-install flow with `getMe` validation and 6-digit pairing-code ownership binding
- [ ] **Phase 10: Bridge Settings, Non-Owner Access & Tool-Use Display** — Master disable, tri-state non-owner policy, tool-use visibility modes
- [ ] **Phase 11: Identity Pre-Install & File-Content Editor** — First-boot idempotent identity seed plus dashboard raw-markdown editor
- [ ] **Phase 12: Dashboard SSE Chat & Hub File Tree** — Unified streaming chat with inline tool-use and read-only `~/hub/` file tree

### Phase Details

#### Phase 8: Bridge Extraction & Supervisor Cutover
**Goal:** Telegram bridge starts and stops as an installable runtime module instead of hard-wired boot code, so every later phase plugs into the same lifecycle surface.
**Depends on:** v1.0 (module registry, manifest, assembler already shipped)
**Requirements:** BRDG-01, BRDG-03 (scaffold), BRDG-04 (scaffold)
**Success Criteria** (what must be TRUE):
  1. Running `python -m bot` with no `TELEGRAM_BOT_TOKEN` env var starts the dashboard cleanly and reports the bridge as "not installed" — no import of `bot.bridge.telegram` in the core boot path.
  2. With the bridge module present in the registry, the supervisor starts polling via `on_start(app_ctx, config)` and calling `on_stop()` shuts the updater down in the documented `updater.stop -> stop -> shutdown` order (verified via log assertions).
  3. A Telethon smoke test confirms install → message round-trips → uninstall → subsequent messages are ignored with no zombie polling loop (re-install from scratch also succeeds).
  4. `TELEGRAM_BOT_TOKEN` becomes optional environment input (bootstrap-only); the bridge module's `config.json` is the canonical source of truth when present.
**Plans:** 3 plans
Plans:
- [x] 08-01-PLAN.md — Supervisor foundation: AppContext, Supervisor, manifest runtime_entry field, registry propagation, Wave 0 test scaffolds
- [x] 08-02-PLAN.md — Bridge extraction: telegram_bridge runtime adapter (on_start/on_stop), modules/bridge -> modules/telegram-bridge rename + migration, lifecycle.uninstall on_stop wiring
- [x] 08-03-PLAN.md — Main.py cutover: D-8.7 boot order, TELEGRAM_BOT_TOKEN removed from required env, one-shot token seed, Telethon e2e smoke, LXC human verification

#### Phase 9: Install Dialog & Owner-Claim FSM
**Goal:** Owner installs and claims the bridge entirely from the dashboard — no `.env` edits, no systemd restarts, no env-var owner gate.
**Depends on:** Phase 8
**Requirements:** BRDG-02, CLAIM-01, CLAIM-02, CLAIM-03, CLAIM-04, SEC-01
**Success Criteria** (what must be TRUE):
  1. Dashboard install dialog accepts a bot token, validates it via Telegram `getMe` before persisting, and rejects malformed/invalid tokens with a clear error message (no partial state written).
  2. After install the dashboard displays a 6-digit pairing code with a TTL countdown and a regenerate button; sending the code to the bot from any Telegram account binds that `user_id` as owner and persists it only in the module's `state.json`.
  3. Pairing attempts are limited to 5 before the code window closes, compared with `hmac.compare_digest`, and expire after 10 minutes; expired/exhausted codes require regeneration.
  4. Owner can revoke ownership from the dashboard; the module returns to pending-claim state and the next pairing-code cycle rebinds a (possibly different) owner.
  5. Bot token is never returned by `GET /api/modules` (only `has_token: bool`) and never appears in any log line — verified by grepping logs after a full install + claim + uninstall cycle; `TELEGRAM_OWNER_ID` env gate is removed from the codebase.
**Plans:** 3 plans
Plans:
- [x] 09-01-PLAN.md — Phase 8 fixes, bridge state module, token install endpoint with getMe validation, token redaction
- [x] 09-02-PLAN.md — Pairing code FSM (HMAC generation/verification), HTMX polling templates, bridge claim handler
- [ ] 09-03-PLAN.md — Auth migration (TELEGRAM_OWNER_ID removal), revoke endpoint, test fixture migration, human verification

#### Phase 10: Bridge Settings, Non-Owner Access & Tool-Use Display
**Goal:** Owner controls runtime bridge behaviour — kill switch, how strangers are treated, and how tool-use is surfaced in Telegram — all from one settings page.
**Depends on:** Phase 9
**Requirements:** BRDG-03, BRDG-04, ACC-01, ACC-02, ACC-03, TUI-01, TUI-02, TUI-03
**Success Criteria** (what must be TRUE):
  1. The bridge settings page exposes a master on/off toggle; when disabled the polling handler short-circuits every update at group `-2` (no owner or non-owner message reaches Claude) and re-enabling resumes polling without reinstall.
  2. Uninstalling the bridge stops the polling task, deletes `state.json` (owner + pairing state), and removes every other module artifact — a fresh reinstall sees no residual owner binding and a new pairing code is required.
  3. Non-owner policy is a dashboard-selectable enum with `drop` (default), `flag`, and `open` modes; `drop` silently ignores, `flag` delivers the message with an `[non-owner user NAME (id=N)]:` envelope prefix to Claude, and `open` treats the sender like an owner.
  4. In `flag` mode the non-owner turn runs with a restricted `allowed_tools` allowlist (no Edit/Write/Bash) — verified by an integration test that issues a write-intent prompt from a non-owner and asserts the SDK refuses the tool call.
  5. Tool-use display has three modes (`temporary`, `persistent`, `hidden`); `temporary` is the default on a fresh install and batch-deletes tool-use messages from the chat when the final answer finishes streaming; `hidden` never emits them; `persistent` leaves them intact.
  6. Bot-token redaction (SEC-01) continues to hold after the settings page lands — `/api/modules/telegram-bridge` and all new settings endpoints return redacted fields and the logs remain token-free.
**Plans:** TBD

#### Phase 11: Identity Pre-Install & File-Content Editor
**Goal:** A freshly-installed Animaya answers like an animaya — never an empty identity — and the owner can edit identity content as raw markdown from the dashboard.
**Depends on:** Phase 8 (parallelizable with 10 — no shared files)
**Requirements:** IDN-01, IDN-02, IDN-03
**Success Criteria** (what must be TRUE):
  1. On first boot the identity module is auto-installed via an idempotent `first_boot_install` hook that writes the default identity file with `open(path, "x")`; running the bot twice never overwrites or clobbers existing Hub identity content.
  2. Dashboard exposes an identity config page listing every identity file in the module scope with a raw-markdown `<textarea>` editor per file; saving persists to `~/hub/knowledge/animaya/` (or the Hub location the module declares).
  3. Edits made in the dashboard are reflected in the next Claude turn's assembled system prompt without restart — verified end-to-end by saving an identity change and seeing it answered in a subsequent Telegram message (and/or dashboard chat once Phase 12 lands).
**Plans:** TBD
**UI hint**: yes

#### Phase 12: Dashboard SSE Chat & Hub File Tree
**Goal:** Owner has a single dashboard page that pairs a streaming Claude chat with a collapsible, read-only view of the whole `~/hub/` tree — the non-Telegram interface to the same assistant.
**Depends on:** Phase 10 (shared tool-use display strategies), Phase 11 (identity present on first boot), Phase 8 (stable supervisor)
**Requirements:** DASH-01, DASH-02, DASH-03, DASH-04, SEC-02
**Success Criteria** (what must be TRUE):
  1. A single dashboard page renders a chat panel next to a collapsible Hub file tree (one URL, one layout) — not two separate pages.
  2. Chat streams Claude responses via SSE and renders tool-use inline using the same strategies as the Telegram bridge's tool-display setting from Phase 10; the owner lock is shared so concurrent Telegram + dashboard turns serialize cleanly.
  3. Claude session keys are namespaced per UI source (`tg:<user_id>` vs `web:<user_id>`) so `--continue` context from Telegram never leaks into a dashboard turn and vice versa — verified by sending distinct context in each UI and confirming it stays separated across at least three turns.
  4. The file tree walks `~/hub/` (knowledge + data + workspace), is collapsible by directory, hides dotfiles by default, and is strictly read-only in v2.0 — no save/delete/rename endpoints exist.
  5. Every file-tree request validates paths via `Path.resolve().is_relative_to(HUB_ROOT.resolve())` and rejects symlinks; a DENY-set blocks `.git/hooks/`, `.ssh/`, `.env*` regardless of traversal; an integration test asserts `../../etc/passwd`, symlinked escapes, and the DENY-set all return 403.
**Plans:** TBD
**UI hint**: yes

### Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 8. Bridge Extraction & Supervisor Cutover | 0/3 | Planned | - |
| 9. Install Dialog & Owner-Claim FSM | 0/3 | Planned | - |
| 10. Bridge Settings, Non-Owner Access & Tool-Use Display | 0/0 | Not started | - |
| 11. Identity Pre-Install & File-Content Editor | 0/0 | Not started | - |
| 12. Dashboard SSE Chat & Hub File Tree | 0/0 | Not started | - |

### Dependencies

- **Critical path:** 8 → 9 → 10 → 12
- **Parallelizable:** 11 can run alongside 10 (no shared files)
- **Research flags:** Phase 10 needs SDK 0.0.25 verification for non-owner `allowed_tools`/`permission_mode`; Phase 12 benefits from an SSE spike (raw `StreamingResponse` vs `sse-starlette`) during planning.

## Backlog

_(999.1 absorbed into Phases 8–10 of v2.0 — removed from backlog.)_

No outstanding backlog items.

### Phase 13: Migrate dashboard frontend to shared frontend-stack-spec

**Goal:** Replace the FastAPI+Jinja+HTMX dashboard with a Next.js 15.5.15 / React 19.2.5 / Tailwind v4 / Bun app that conforms to `~/hub/knowledge/references/frontend-stack-spec.md`. Author a new shared UI style spec extracted from `homelab/apps/admin` (D-12). Demote FastAPI to a loopback-only engine (D-01); Next.js owns port 8090. Land the Phase 12 SSE chat + Hub file tree natively in Next.js (D-09 reorder: Phase 13 ships before Phase 12).
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, SEC-01, SEC-02 (plus D-01..D-15 locked decisions in 13-CONTEXT.md)
**Depends on:** Phase 11 (OWNER.md contract for D-07 gate)
**Plans:** 1/6 plans executed

Plans:
- [x] 13-01-PLAN.md — Scaffold dashboard/, author ~/hub/knowledge/references/ui-style-spec.md, Playwright harness (Wave 1)
- [ ] 13-02-PLAN.md — next-auth Credentials(telegram) provider, OWNER.md gate, DASHBOARD_TOKEN bypass middleware, CSRF/engine/redact helpers (Wave 2)
- [ ] 13-03-PLAN.md — All /api/** route handlers: modules, bridge, hub tree/file, SSE chat proxy, zod schemas (Wave 3, parallel with 13-04)
- [ ] 13-04-PLAN.md — Python loopback engine (bot/engine/*) with owner-lock + SSE generator, bot/main.py supervises both processes (Wave 3, parallel with 13-03)
- [ ] 13-05-PLAN.md — Pages: chat+tree unified page, login widget, modules/bridge with rhf+zod, 7 Playwright E2E specs (Wave 4)
- [ ] 13-06-PLAN.md — Cutover: delete bot/dashboard/*, Bun-stage Dockerfile, ROADMAP reorder, manual LXC smoke (Wave 5, checkpoint)
