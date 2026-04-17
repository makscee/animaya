# Phase 9: Install Dialog & Owner-Claim FSM - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-04-16
**Phase:** 09-install-dialog-owner-claim-fsm
**Mode:** --auto (all decisions auto-selected from recommended defaults)
**Areas discussed:** Token install UX, getMe validation, Pairing code mechanics, FSM state structure, Dashboard auth migration, Phase 8 integration fixes

---

## Phase 8 Integration Fixes

| Option | Description | Selected |
|--------|-------------|----------|
| Fix as Phase 9 prerequisites | Include supervisor app.state fix, uninstall supervisor arg, typing fix in Plan 1 | Y |
| Separate Phase 8.1 | Create decimal phase for fixes | |
| Defer to Phase 10 | Fix when needed for settings page | |

**User's choice:** [auto] Fix as prerequisites (recommended -- blocks Phase 9 install/uninstall flows)
**Notes:** Audit found 2 integration gaps + 1 tech debt item from Phase 8

## Token Install UX

| Option | Description | Selected |
|--------|-------------|----------|
| Single form on config page | Extend existing /modules/{name}/config with token input | Y |
| Multi-step wizard | Separate install wizard page with progress steps | |
| Modal dialog | Overlay modal on modules list page | |

**User's choice:** [auto] Single form on config page (recommended -- follows existing pattern)

## getMe Validation

| Option | Description | Selected |
|--------|-------------|----------|
| Direct httpx GET | httpx.get(api.telegram.org/bot{token}/getMe) | Y |
| python-telegram-bot SDK | Import and use Bot(token).get_me() | |

**User's choice:** [auto] Direct httpx (recommended -- simpler, no extra import)

## Pairing Code Mechanics

| Option | Description | Selected |
|--------|-------------|----------|
| 6-digit numeric + HTMX poll | secrets.SystemRandom, hx-get polling every 5s | Y |
| 6-char hex + SSE | token_hex(3) with SSE push on claim | |
| 6-digit + manual refresh | No auto-polling, user clicks refresh | |

**User's choice:** [auto] 6-digit numeric + HTMX poll (recommended -- consistent with dashboard patterns)

## FSM State Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Flat JSON in state.json | claim_status + owner_id + code_hash + expires + attempts | Y |
| Nested JSON | Separate claim and code sub-objects | |
| SQLite | Structured storage for FSM transitions | |

**User's choice:** [auto] Flat JSON (recommended -- matches existing state.json pattern)

## Dashboard Auth Migration

| Option | Description | Selected |
|--------|-------------|----------|
| Read owner from state.json | Replace env gate with state.json lookup; open when unclaimed | Y |
| Keep env as fallback | state.json primary, env var secondary | |
| Separate owner store | New owner.json at data root | |

**User's choice:** [auto] Read from state.json (recommended -- single source of truth)

---

## Claude's Discretion

- HMAC key derivation details
- HTMX template structure for countdown
- Error message wording
- Bot username display after getMe
- Test partitioning

## Deferred Ideas

- QR-code pairing (REQUIREMENTS.md future)
- Multi-owner support
- on_start retry-with-backoff
