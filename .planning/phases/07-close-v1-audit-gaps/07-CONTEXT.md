# Phase 07: Close v1.0 Audit Gaps - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning
**Source:** Express path — derived from `.planning/v1.0-MILESTONE-AUDIT.md` + ROADMAP Phase 7 section

<domain>
## Phase Boundary

Retroactive verification/documentation cleanup for already-shipped v1.0 work. **No new feature code.** Produce missing VERIFICATION.md/VALIDATION.md artifacts, reconcile REQUIREMENTS.md checkboxes + traceability table, and get `/gsd-audit-milestone 1.0` to pass.

In scope:
- Create `02-VERIFICATION.md`, `03-VERIFICATION.md`, `05-VERIFICATION.md` retroactively
- Create `02-VALIDATION.md`, `06-VALIDATION.md` retroactively; complete Nyquist sign-off for all 6 phases
- Update `REQUIREMENTS.md` checkboxes + traceability table so they match shipped reality
- Verify previously-unresolved DASH-02, DASH-04, DASH-05 against shipped Phase 5 code

Out of scope:
- New features; bug fixes beyond what verification surfaces (surface them as tech debt entries)
- Addressing Phase 2 streaming double-bubble bug (already deferred per audit)

</domain>

<decisions>
## Implementation Decisions

### Verification approach
- Use `gsd-verifier` agent for each retroactive VERIFICATION.md (one per phase: 02, 03, 05)
- Verifier runs goal-backward analysis against the **shipped code in repo**, not just plans/SUMMARY files
- Per-requirement verdict: SATISFIED / UNSATISFIED / PARTIAL + evidence (file:line refs, test refs)
- If a requirement is unsatisfied and cannot be satisfied without new code: mark UNSATISFIED with explicit gap acknowledgement (acceptable for audit close per success criteria)

### Validation / Nyquist
- Create `02-VALIDATION.md` and `06-VALIDATION.md` from `$HOME/.claude/get-shit-done/templates/VALIDATION.md`
- For all 6 phases, add Nyquist sign-off (`nyquist_compliant: true` frontmatter + checklist) once VALIDATION + coverage pass
- If a validation dimension legitimately lacks coverage, document gap inline rather than fabricate coverage

### REQUIREMENTS.md bookkeeping
- Update checkboxes `[ ]` → `[x]` where shipped + verified
- Update traceability table: set phase + status per REQ-ID based on freshly-produced VERIFICATION.md results
- Insert `TEST-01..03` entries for Phase 6 telethon harness (audit flagged missing)
- Reality source: post-plan VERIFICATION.md + SUMMARY.md frontmatters

### DASH-02 / DASH-04 / DASH-05
- Currently marked unsatisfied in audit — no SUMMARY frontmatter `requirements_satisfied` entry
- Verifier must inspect shipped dashboard code (`bot/dashboard/app.py`, `dashboard/src/`) and decide: satisfied / partial / unsatisfied
- If satisfied: promote in VERIFICATION.md + REQUIREMENTS.md. If unsatisfied: mark explicitly; success criterion accepts this.

### Plan layout (from ROADMAP)
1. `07-01-PLAN.md` — Retroactive `02-VERIFICATION.md` (TELE-01..05) against bridge code
2. `07-02-PLAN.md` — Retroactive `03-VERIFICATION.md` (MODS-01..06) against module system code
3. `07-03-PLAN.md` — Retroactive `05-VERIFICATION.md` (DASH-01..06 incl. 02/04/05) against dashboard code
4. `07-04-PLAN.md` — Missing VALIDATION.md (02, 06) + Nyquist sign-off for all 6 phases
5. `07-05-PLAN.md` — REQUIREMENTS.md bookkeeping (checkboxes, traceability, TEST-01..03 insertion)

### Claude's Discretion
- Exact plan task granularity within each PLAN.md
- Whether to split 07-04 into two plans if Nyquist sign-off work balloons
- Specific evidence format inside each VERIFICATION.md (keep consistent with existing `01-VERIFICATION.md`, `04-VERIFICATION.md` style)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Audit source of truth
- `.planning/v1.0-MILESTONE-AUDIT.md` — Gap inventory; every plan traces back here
- `.planning/ROADMAP.md` — Phase 7 section with the 5 pre-sketched plans + success criteria
- `.planning/REQUIREMENTS.md` — Target for bookkeeping updates (checkboxes + traceability table)

### Verification style references (read before writing new VERIFICATION.md)
- `.planning/phases/01-install-foundation/01-VERIFICATION.md` — Passed exemplar
- `.planning/phases/04-first-party-modules/04-VERIFICATION.md` — Passed exemplar (11/11)
- `.planning/phases/06-telethon-test-harness-at-hub-level-for-end-to-end-telegram-b/` — Recent VERIFICATION.md

### Validation template
- `$HOME/.claude/get-shit-done/templates/VALIDATION.md` — Use for 02, 06 creation; copy structure from existing `03-VALIDATION.md`/`04-VALIDATION.md`/`05-VALIDATION.md`

### Code scopes for verifier
- Phase 02 (bridge): `bot/bridge/telegram.py`, `bot/bridge/formatting.py`, `bot/claude_query.py`
- Phase 03 (modules): `bot/dashboard/app.py` module endpoints, `bot/templates/modules/`, module system code in `bot/`
- Phase 05 (dashboard): `bot/dashboard/app.py` (all endpoints), `dashboard/src/` (Next.js frontend)

### Live environment (for manual spot-checks only, not required)
- animaya-dev LXC 205 on tower — see `~/.claude/.../reference_animaya_dev_lxc.md`

</canonical_refs>

<specifics>
## Specific Ideas

- Verifier agent is `gsd-verifier` (already exists, used in prior phases)
- REQUIREMENTS.md edits should be atomic per REQ-ID group; don't batch into one giant commit
- Each plan produces one artifact (or cluster); keep commits aligned to plan boundaries
- Phase 6 is already VERIFIED per audit but lacks VALIDATION.md — belongs in 07-04 scope
- TEST-01..03 are Phase 6 telethon harness requirements missing from traceability table — add rows during 07-05

</specifics>

<deferred>
## Deferred Ideas

- Phase 2 streaming double-bubble bug (noted in audit tech_debt; deferred to future streaming-robustness phase)
- Phase 6 extra out-of-plan test files (login_helper.py, etc.) — harmless per audit, no cleanup needed
- Integration/E2E audit dimensions (audit marked them `deferred`; not in Phase 7 scope)

</deferred>

---

*Phase: 07-close-v1-audit-gaps*
*Context gathered: 2026-04-15 via express path (gap-closure phase, no design discussion needed)*
