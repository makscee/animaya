# Project Retrospective

## Milestone: v1.0 — Audit Gaps

**Shipped:** 2026-04-15
**Duration:** ~3 days (2026-04-13 to 2026-04-15)
**Phases:** 7
**Plans:** 29
**Requirements:** 27/27 v1 satisfied + 3 test harness

### What Was Built

A complete personal AI assistant platform from scratch:

1. **Install & Foundation** — `setup.sh` + `run.sh` + systemd service; CLAUDECODE=1 env sanitization; auto-restart on crash/reboot
2. **Telegram Bridge** — Streaming Claude Code responses via python-telegram-bot; per-user asyncio locks; typing indicator; chunked long messages; graceful error surfacing
3. **Module System** — Pydantic-validated manifests; atomic JSON registry; install/uninstall lifecycle scripts; CLAUDE.md assembler (install-order + XML wrapping); AST-based isolation enforcement; zero-artifact-leakage guarantee
4. **First-Party Modules** — Identity (onboarding ConversationHandler, XML prompt injection, reconfigure via `/identity`); Memory (Haiku consolidation, Hub markdown, post-reply trigger); Git-versioning (asyncio commit loop, single-committer Lock, scoped commits)
5. **Web Dashboard** — FastAPI + Jinja2 + HTMX; Telegram Login Widget HMAC auth; itsdangerous sessions; live status via 5s HTMX polling; async install/uninstall job runner with 409 concurrency guard; JSON Schema → HTMX form renderer
6. **Telethon Test Harness** — MTProto auth + session persistence at ~/hub/telethon/; `send_to_bot` / `wait_for_reply` / `assert_contains` driver API; smoke test PASSES live against @mks_test_assistant_bot
7. **Audit Gap Closure** — Retroactive VERIFICATION.md for phases 02/03/05; retroactive VALIDATION.md for phases 02/06; Nyquist sign-off pass; REQUIREMENTS.md checkboxes and traceability reconciled

### What Worked

- **Port-first strategy for bridge (Phase 2):** Porting v1 bridge verbatim avoided streaming regressions. Proven chunking/lock logic worked immediately.
- **Wave-0 infrastructure plans:** Dedicating plan 00 to test scaffolding and fixtures before feature work meant every phase had working tests from the start.
- **Pydantic for module validation:** Schema-first approach caught manifest errors early and made the isolation contract explicit.
- **HTMX over npm:** Eliminating the frontend build toolchain removed an entire class of dependency and deployment problems.
- **Telethon harness at hub level:** Placing the harness in ~/hub (not inside animaya) made it reusable and accessible from any Claude Code agent.
- **Phase 07 audit-driven gap closure:** Running `gsd-audit-milestone` before closing v1.0 surfaced real gaps (missing VERIFICATION.md files) and forced their resolution, resulting in a clean audit trail.

### What Was Inefficient

- **Roadmap progress table not updated during execution:** The ROADMAP.md progress table was initialized with placeholder states and never auto-updated, requiring manual reconciliation at milestone close.
- **Nyquist sign-off gap:** Three phases (01, 03, 05) completed VERIFICATION.md but not VALIDATION.md sign-off. Retroactive completion was necessary — would be better enforced at phase transition time.
- **STATE.md metrics section:** Velocity tracking fields were never populated during execution, reducing the utility of that section.
- **Double-bubble streaming artifact:** A cosmetic streaming defect (duplicate message bubbles under high latency) was identified but deferred rather than fixed inline. Carries forward as tech debt.

### Patterns Established

- **LXC-native module pattern:** Folder + manifest.json + install.sh/uninstall.sh is proven for Animaya modules. Reuse this pattern for v2 modules.
- **Hub knowledge/ for module state:** Identity, memory, and git-versioning all store state in ~/hub/knowledge/ — this is the established data home for module state.
- **Telethon smoke test as acceptance gate:** Running the Telethon harness before milestone close is the established end-to-end acceptance test for Telegram functionality.
- **CLAUDE.md assembler via XML blocks:** Module system prompts are XML-wrapped and merged in install order. This pattern works and should be preserved in v2.
- **Tech debt register:** Streaming artifact and Nyquist gaps are explicitly tracked in MILESTONES.md. This register should be reviewed at v2.0 kickoff.

### Key Lessons

1. **Audit before archiving is worth it.** Running gsd-audit-milestone before declaring v1.0 done surfaced real documentation gaps. The extra Phase 07 investment paid off in a clean, traceable archive.
2. **Wave-0 plan is non-negotiable.** Every phase that started with a wave-0 infrastructure plan had smoother execution. Phases without it accumulated test debt.
3. **Port proven code, rewrite structure.** The right call for the bridge was to port the streaming/lock logic verbatim while rewriting the module boundary. Rewriting everything from scratch would have introduced unnecessary risk.
4. **HTMX is enough for internal tools.** The dashboard requirements were fully met without React/Next.js. For internal tooling, HTMX + Jinja2 is sufficient and faster to ship.

### Cost Observations

- Milestone completed in ~3 days of focused GSD execution
- 7 phases, 29 plans, 30 requirements covered
- Phase 07 (audit gap closure) added ~5 plans of retroactive documentation work — ~17% overhead on a 24-plan milestone. Expected for first milestone with full audit process.

## Cross-Milestone Trends

### Process Evolution

- v1.0: First GSD milestone with full audit trail. Established baseline: wave-0 plans, pydantic-first, HTMX dashboard, Telethon acceptance gate.

### Cumulative Quality

- v1.0: 27/27 REQ satisfied. tech_debt status (non-blocking). Clean archive. Telethon smoke PASS.

### Top Lessons (Verified Across Milestones)

- Audit before archive (v1.0 — confirmed)
- Wave-0 infra plan per phase (v1.0 — confirmed)
- Port proven streaming code, don't rewrite (v1.0 — confirmed)
