# Project Research Summary

**Project:** Animaya v2.0 — Onboarding Polish & Bridge-as-Module
**Domain:** LXC-native modular Claude Code assistant (Telegram + FastAPI/HTMX dashboard), personal single-user
**Researched:** 2026-04-15
**Confidence:** HIGH

## Executive Summary

Animaya v2.0 is a cohesive refactor, not a greenfield build: every target feature maps to mechanics already proven in v1.0. The recommended approach is to extract the Telegram bridge from `bot/main.py` into a first-class installable runtime module, then layer onboarding UX (token install dialog, 6-digit pairing-code owner-claim, bridge settings page), a pre-installed identity module with a raw-markdown editor, and two new dashboard pages (streaming chat with inline tool-use, plus a read-only `~/hub/` file tree). All of this ships on the existing stack — FastAPI + Jinja2 + HTMX + python-telegram-bot v21 + Claude Code SDK — with zero new pip dependencies; the only asset addition is vendored htmx 2.0.8 + htmx-ext-sse for dashboard chat streaming.

The architecture inverts v1.0's startup path: a module supervisor in `bot/main.py` replaces the hardcoded bridge boot, iterating the registry and calling `start(app_ctx, config)` / `stop()` on each runtime module. `TELEGRAM_BOT_TOKEN` demotes from required env to module config; `TELEGRAM_OWNER_ID` is replaced entirely by the pairing-code FSM persisted in `state.json`. Bridge and dashboard chat funnel through a single `build_options(sender_meta=...)` factory so owner/non-owner/channel context stays consistent. Session drift is the other core concern: owner sessions must be keyed by owner id (not transport) with the existing per-user asyncio lock serializing Telegram and dashboard turns.

Key risks cluster around security and lifecycle hygiene: (1) bot token leaking through logs, `/api/modules` responses, or git-committed Hub files; (2) 6-digit pairing brute-force (10^6 space through Telegram itself) without TTL + attempt-cap + `hmac.compare_digest`; (3) path traversal in the Hub file tree that could read `/etc/animaya/bridge.env` or write `.git/hooks/` for RCE; (4) prompt injection via non-owner Telegram display names when sender metadata is naively concatenated into the system prompt; (5) zombie polling loops after uninstall if PTB's `updater.stop -> stop -> shutdown` sequence is short-circuited. Each is addressable with documented patterns (SecretStr + systemd drop-in, attempt-cap + TTL, `Path.resolve().is_relative_to(HUB_ROOT)` + DENY-set, structural isolation + restricted `allowed_tools` for non-owners, explicit lifecycle contract) — but all must be designed in, not bolted on.

## Key Findings

### Recommended Stack

Zero new runtime dependencies. Every v2.0 feature ships on the validated v1.0 stack. The single additive change is vendoring `htmx.min.js` 2.0.8 and `htmx-ext-sse.min.js` into `bot/dashboard/static/` for streaming chat (LXC may be air-gapped; no CDN). Optional UX libraries (Pygments, markdown-it-py, watchfiles) are deliberately deferred — revisit after first-user feedback.

**Core technologies:**
- **FastAPI >=0.115 + Uvicorn >=0.30 + Jinja2 >=3.1** — existing dashboard; add `/chat`, `/hub/*`, `/modules/telegram-bridge/*` routes as Jinja fragments.
- **HTMX 2.0.8 + htmx-ext-sse (vendored)** — all new interactivity; SSE streams Claude tokens; lazy-load Hub tree.
- **python-telegram-bot >=21.10** — manual `initialize()/start()/updater.start_polling()` at module install; `stop()/shutdown()` on uninstall.
- **claude-code-sdk >=0.0.25** — bridge + dashboard share `build_options(sender_meta=...)`; `StreamingResponse(media_type="text/event-stream")` for dashboard chat.
- **Python stdlib only** for new logic: `secrets.randbelow` (pairing code), `hmac.compare_digest` (constant-time), `pathlib.Path.resolve().is_relative_to()` (tree guard), `asyncio.Lock` (owner lock), `json` (module config + `state.json`).

Full detail: `.planning/research/STACK.md`.

### Expected Features

**Must have (table stakes):**
- Token input field in install dialog with `getMe` validation + redaction after save (`••••••••1234`).
- 6-digit pairing-code owner-claim (WhatsApp Web / Discord mental model) with TTL + regenerate.
- Master bridge on/off toggle (emergency stop; early-exit handler pre-`_owner_gate`).
- Tool-use display setting: `temporary` (default) / `persistent` / `hidden` — matches Cursor/Zed/Claude.ai conventions.
- Streaming dashboard chat with inline tool-use matching Telegram UX.
- Lazy-loaded Hub file tree with markdown/text/image viewer; dotfiles hidden by default.
- "Already configured" state detection in module pages; non-owner auto-drop with audit event.

**Should have (differentiators):**
- Pairing-code claim with self-healing owner config — no `.env` edits, no systemd restart.
- Non-owner access as metadata-flag (envelope prefix `[non-owner user NAME (id=N)]:`) with policy enum `drop`/`flag`/`open` — owner-curated gatekeeping, not just silent block.
- Identity pre-installed on first boot with raw-markdown file editor (live system-prompt preview) — power users get full control.
- Unified `~/hub/` tree exposing `knowledge/`, `backlog/`, `workspace/` — trust through transparency.

**Defer (v2.x / v3+):**
- File editing from Hub tree (gated on git-versioning trust).
- Pairing-code QR / tool-argument expansion / chat history browser.
- Per-group bridge binding; voice input in dashboard chat; multi-identity switching.

Full detail: `.planning/research/FEATURES.md`.

### Architecture Approach

v2.0 inverts the startup path: `bot/main.py` no longer imports `bot.bridge.telegram`. Instead a module supervisor iterates `registry.list_active()` and dispatches `on_start(app_ctx, config)` / `on_stop()` for each runtime module in the same event loop as Uvicorn. `TELEGRAM_BOT_TOKEN` and `TELEGRAM_OWNER_ID` become optional env (bootstrap only); module `config.json` + `state.json` own runtime state. Bridge + dashboard-chat both call `bot.claude_query.build_options(sender_meta=...)` so the system prompt, cwd, and tool allowlist stay single-source.

**Major components:**
1. **Module supervisor** (`bot/main.py` + `bot/modules/registry.py` + `bot/modules/lifecycle.py`) — enumerates active modules at boot; dispatches install/uninstall/reconfigure hooks; owns asyncio task lifetimes.
2. **`telegram-bridge` runtime module** (`bot/modules_runtime/telegram_bridge/`) — extracted from `bot/bridge/`; adds `claim.py` (6-digit FSM + `state.json` with `{phase, code, expires_at, owner_id, attempts}`) and `tool_display.py` (off/summary/detailed strategies).
3. **Identity runtime module** (`bot/modules_runtime/identity/`) — adds `first_boot_install(data_dir)` called when `config.json` missing; writes default `~/hub/knowledge/animaya/identity.md` idempotently (`open(path, "x")`).
4. **Dashboard chat subsystem** (`bot/dashboard/sse.py` + `chat_routes.py`) — in-process `EventBus` (asyncio.Queue fan-out); `POST /api/chat` spawns SDK query; `GET /api/chat/stream` SSE-serves deltas; tool-use rendered inline via shared strategies.
5. **Hub file tree subsystem** (`bot/dashboard/files_routes.py`) — `GET /hub`, `GET /hub/tree?path=`, `GET /hub/file?path=`; path-traversal guard via `resolved.is_relative_to(HUB_ROOT.resolve())` + symlink rejection + DENY-set for `.git/`, `.env`, `*.pem`, `id_*`.

Full detail: `.planning/research/ARCHITECTURE.md`.

### Critical Pitfalls

1. **Bot token leak via logs / `config.json` / dashboard responses.** Store in systemd drop-in (`/etc/animaya/bridge.env`, mode 0600); pydantic `SecretStr` with redacted `model_dump`; scrub token substring in error logs; `/api/modules` returns `has_token: bool` only.
2. **Pairing-code brute force (10^6 space through Telegram).** Enforce TTL (10 min), attempt-cap (5 failures -> close window), `hmac.compare_digest`, one-shot consumption, per-attempt audit log.
3. **Path traversal in Hub file tree.** Canonical `resolved = (HUB_ROOT / user_path).resolve(); assert resolved.is_relative_to(HUB_ROOT.resolve())`; reject symlinks via `os.path.realpath`; DENY-set covers `.git/`, `.env`, keys; read-only by default.
4. **Prompt injection via non-owner sender metadata.** Structural isolation (not tags); strip control chars/XML/backticks from `first_name`/`username`; truncate non-owner messages to 500 chars; apply restricted `allowed_tools` (read-only) or `permission_mode="plan"` on non-owner turns; system-prompt guard treats `[non-owner]` envelope as untrusted input.
5. **Uninstall leaves polling loop running; reinstall double-polls.** Explicit lifecycle contract: `await updater.stop(); await app.stop(); await app.shutdown()` in order. File lock `/run/animaya/bridge.lock` rejects second start. Call `deleteWebhook?drop_pending_updates=true` before fresh polling. Integration test: install -> send -> uninstall -> send -> must be ignored.

Other high-value pitfalls covered in `.planning/research/PITFALLS.md`: tool-use delete artifacts (429s), identity clobber on reinstall (use `open(path, "x")` + git-diff guard), dashboard/Telegram session drift (share per-owner asyncio lock).

## Implications for Roadmap

The architecture research already produced a dependency-justified build order (P1–P12); the roadmap should fold this into coherent phases that each deliver a demoable vertical slice.

### Phase 1: Bridge Extraction & Supervisor Cutover
**Rationale:** Everything else depends on the bridge being an installable module. This is the riskiest refactor (startup path, test imports, env-var deprecation) so it ships first behind a thin shim.
**Delivers:** `bot/bridge/` moved to `bot/modules_runtime/telegram_bridge/`; `bot/modules/lifecycle.py` gains `on_start`/`on_stop`; `bot/main.py` iterates `registry.list_active()` instead of hardcoded bridge boot; `TELEGRAM_BOT_TOKEN` becomes optional env.
**Addresses:** table-stakes bridge-as-module plumbing (MODS extension, TELE migration).
**Avoids:** Pitfall 5 (uninstall lifecycle) — explicit `updater.stop -> stop -> shutdown` contract lands with the supervisor.
**Uses:** PTB v21 manual lifecycle; existing module manifest system.

### Phase 2: Install Dialog + Owner-Claim FSM
**Rationale:** Bridge module is useless without a way to configure it. Install UX (token input, `getMe` validate) + claim FSM + `state.json` land together because they share the registry config path.
**Delivers:** `modules/telegram-bridge/{install,uninstall,reconfigure}.py`; token field in install dialog with redaction; 6-digit pairing-code FSM persisted in `state.json`; dashboard displays code with TTL countdown + regenerate button; claim handler in `polling.py` completes ownership binding.
**Addresses:** table-stakes pairing UX; differentiator self-healing owner config.
**Avoids:** Pitfall 1 (token leak — SecretStr + systemd drop-in) and Pitfall 2 (brute-force — TTL + attempt-cap + `hmac.compare_digest`).
**Uses:** `secrets.randbelow`, `hmac.compare_digest`, pydantic SecretStr, systemd drop-in pattern.

### Phase 3: Bridge Settings Page + Non-Owner Policy
**Rationale:** Once owner-claim works, layered settings (master disable, non-owner policy, tool-use display) build on the same config schema. Non-owner sender metadata must ship with restricted tool allowlist — design-gated feature.
**Delivers:** `/modules/telegram-bridge/settings` HTMX page; master-disable TypeHandler at `group=-2`; non-owner policy enum (`drop`/`flag`/`open`, default `drop`); envelope prefix `[non-owner user NAME (id=N)]:`; `sender_meta` passthrough in `build_options()`; tool-use display mode setting (`temporary` default).
**Addresses:** table-stakes master disable + tool-use visibility; differentiator metadata-flag non-owner access.
**Avoids:** Pitfall 4 (prompt injection — sanitize sender fields, restricted `allowed_tools` for non-owners, system-prompt guard) and Pitfall 6 (tool-use artifacts — batch delete at turn end, `contextlib.suppress(BadRequest)`, toggle-off path).

### Phase 4: Identity Pre-Install + File-Content Editor
**Rationale:** Parallelizable with Phase 3 (no shared files). First-boot UX: fresh dashboard never shows empty bot; identity edit is the blueprint for future module file editors.
**Delivers:** `first_boot_install(data_dir)` hook in `bot/main.py`; default `~/hub/knowledge/animaya/identity.md` seeded idempotently; `/modules/identity/edit` HTMX page with `<textarea>` save + live system-prompt preview; shared file-viewer component reused by Hub tree.
**Addresses:** differentiator identity pre-installed with raw-markdown editor.
**Avoids:** Pitfall 7 (identity clobber — `open(path, "x")`, schema-version tag, git-diff guard before overwrite).

### Phase 5: Dashboard SSE Bus + Streaming Chat + Inline Tool-Use
**Rationale:** Largest new surface; depends on Phase 3's tool-display strategies (shared rendering) and Phase 1's stable supervisor. Ships after bridge stabilizes so owner-lock semantics are already correct.
**Delivers:** `bot/dashboard/sse.py` (EventBus); `chat_routes.py` (`POST /api/chat`, `GET /api/chat/stream`); vendored htmx 2.0.8 + htmx-ext-sse; Jinja fragments for user/assistant/tool-use turns; per-owner asyncio lock shared with bridge; namespaced session keys (`tg:<id>` vs `web:<id>`) to prevent Claude `--continue` contamination.
**Addresses:** table-stakes streaming chat + inline tool-use.
**Avoids:** Pitfall 8 (session drift — single per-owner lock, dedup via `last_event_id`, "active on Telegram" indicator).

### Phase 6: Hub File Tree (Read-Only)
**Rationale:** Parallelizable with Phases 3–5 after Phase 1. Security-critical but scope-contained.
**Delivers:** `/hub` tree page; `GET /hub/tree?path=` (HTMX lazy-expand nested `<ul>`); `GET /hub/file?path=` (markdown/text/image viewer); dotfiles hidden by default; path-traversal guard + symlink rejection + DENY-set.
**Addresses:** differentiator unified `~/hub/` tree.
**Avoids:** Pitfall 3 (path traversal — canonical prefix check, symlink realpath rejection, DENY-set, read-only).

### Phase Ordering Rationale

- **P1 before all:** Every v2.0 feature assumes bridge-as-module. Shipping it first behind a shim makes subsequent phases additive, not retrofitting.
- **P2 before P3:** Settings page needs config schema and claim FSM to exist.
- **P4 parallel with P3:** No shared files; independent risk surface.
- **P5 after P3:** Tool-display strategies are shared between Telegram and dashboard chat — build once in P3, reuse in P5.
- **P6 parallel anywhere after P1:** File tree is self-contained; security-gated but independently reviewable.
- **Critical path:** P1 -> P2 -> P3 -> P5. P4 and P6 fan out independently.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (non-owner policy):** Prompt-injection mitigation patterns for Claude Code SDK are evolving; confirm `permission_mode="plan"` semantics and verify restricted `allowed_tools` list against SDK 0.0.25 behavior with Telethon harness.
- **Phase 5 (SSE bus):** FastAPI SSE + HTMX + asyncio cancel-on-disconnect has subtle edge cases (zombie connections, backpressure). Recommend a spike with `sse-starlette`'s `EventSourceResponse` vs raw `StreamingResponse` before committing.

Phases with standard patterns (skip research-phase):
- **Phase 1 (extraction):** Pure refactor; code inspection already nailed down the seams.
- **Phase 2 (claim FSM):** WhatsApp/Discord patterns well-established; stdlib primitives adequate.
- **Phase 4 (identity editor):** Trivial HTMX textarea pattern; already precedent in v1 module forms.
- **Phase 6 (file tree):** Path-guard pattern documented; lazy-load standard.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Code inspection of `bot/dashboard/`, `bot/bridge/`, `bot/modules/`, `pyproject.toml`; PTB v21 docs; htmx 2.0.8 current stable verified. |
| Features | HIGH | Cross-validated with WhatsApp/Discord/Matrix pairing UX; Claude.ai/Cursor/Zed tool-display patterns; GitHub/VSCode file-tree conventions. v1.0 shipped all adjacent mechanics. |
| Architecture | HIGH | Grounded in current repo HEAD (5486302); no external ecosystem guesswork; seams identified by reading actual imports. |
| Pitfalls | HIGH | System-specific; anchored to real v1 files (`bot/bridge/telegram.py`, `bot/dashboard/auth.py`, `bot/modules/lifecycle.py`); each pitfall has concrete file reference. |

**Overall confidence:** HIGH

### Gaps to Address

- **Non-owner `permission_mode`/`allowed_tools` exact values.** Research identified the pattern (restricted mode for non-owner turns) but SDK-specific enum values need verification against `claude-code-sdk` 0.0.25 during Phase 3 planning. Mitigation: read SDK source at planning time; have Telethon harness ready to verify injection resistance.
- **Identity editor "system-prompt preview" UX.** Differentiator is novel (no competitor ships this). First-user feedback required to validate presentation. Ship minimal viable preview in Phase 4, iterate post-launch.
- **SSE disconnect/reconnect semantics under HTMX.** `htmx-ext-sse` reconnects automatically; must design dedup (`last_event_id`) carefully to avoid replaying deltas. Spike during Phase 5 planning.
- **Session-key namespacing rollout.** Changing from `user_id` to `tg:<id>`/`web:<id>` mid-Phase-5 may orphan existing Claude `--continue` state. Decide migration path (fresh session vs best-effort migration) before Phase 5 lands.
- **Pre-install identity on v1->v2 upgrade.** Idempotency handles fresh installs; upgrade path from v1 must be tested explicitly (existing Hub with identity present must NOT be re-seeded).

## Sources

### Primary (HIGH confidence)
- Repo HEAD (5486302): `bot/main.py`, `bot/bridge/telegram.py`, `bot/dashboard/{app,auth,deps,module_routes}.py`, `bot/modules/{registry,lifecycle,manifest,assembler}.py`, `pyproject.toml`.
- `.planning/PROJECT.md` (v2.0 milestone scope) and `.planning/v1.0-MILESTONE-AUDIT.md` (prior tech-debt carryover).
- Recent commits `4c2783c`, `5ebd0a8`, `e22f557`, `992332f`, `5486302` — auth + owner-gate + bridge-module-backlog history.
- python-telegram-bot v21.6 Application docs — `initialize/start/stop/shutdown` lifecycle.
- htmx releases + htmx SSE extension docs — 2.0.8 current stable; streaming chat pattern.
- FastAPI StreamingResponse + Python `secrets` module documentation.

### Secondary (MEDIUM confidence)
- WhatsApp Help Center — Link device with phone number (6-digit pairing UX).
- Claude Code issue #35932 — compact tool-display request validates "temporary default".
- Claude.ai generative UI analysis — tool-display patterns.
- Prompt-injection research (Greshake et al.) — indirect injection risk framing.

### Tertiary (LOW confidence)
- Optional UX libs (Pygments, markdown-it-py, watchfiles) — recommendation to defer based on judgment; validate with first-user feedback.
- Non-owner "flag" policy UX — project-novel; mechanics natural (envelope prefix pattern from v1) but user expectations unestablished.

---
*Research completed: 2026-04-15*
*Ready for roadmap: yes*
