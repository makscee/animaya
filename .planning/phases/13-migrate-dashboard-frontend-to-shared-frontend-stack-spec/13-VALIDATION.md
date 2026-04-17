---
phase: 13
slug: migrate-dashboard-frontend-to-shared-frontend-stack-spec
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-17
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Populated by planner in step 8 based on RESEARCH.md Validation Architecture section.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + Playwright (E2E) + Telethon (Telegram smoke) |
| **Config file** | pyproject.toml / playwright.config.ts (Wave 0 to install) |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v && npx playwright test` |
| **Estimated runtime** | ~60 seconds quick / ~180 seconds full |

---

## Sampling Rate

- **After every task commit:** quick pytest
- **After every plan wave:** full suite + Playwright
- **Before `/gsd-verify-work`:** Full suite green + Telethon smoke
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Plan.Task | Req | Command |
|-----------|-----|---------|
| 13-01.1 | D-12 | `grep -q 'OBSOLETE' /Users/admin/hub/knowledge/voidnet/ui-spec.md` |
| 13-01.2 | D-13, D-14 | `cd dashboard && bunx tsc --noEmit` |
| 13-01.3 | D-11 | `cd dashboard && bunx playwright test --list` |
| 13-02.* | D-06, D-07, Telegram HMAC | `cd dashboard && bun test lib/` |
| 13-03.* | SEC-01, SEC-02 | `cd dashboard && bun test app/api/` |
| 13-04.* | DASH-01..04 | `cd dashboard && bunx playwright test` |
| 13-05.* | D-03 | `pytest tests/engine/ -v` |
| 13-06.* | D-01, D-08 | `rg -n 'itsdangerous\|Jinja2' bot/ \|\| echo ok` + full suite |

---

## Wave 0 Requirements

- [x] `dashboard/package.json` — Next.js 15.5.15, React 19.2.5, Tailwind 4.2.2 pinned per spec (13-01.2)
- [x] `dashboard/playwright.config.ts` — E2E harness for dashboard parity (13-01.3)
- [x] `dashboard/tests/e2e/fixtures.ts` — auth + owner + Telegram HMAC fixtures (13-01.3)
- [ ] Bun layer in `docker/Dockerfile.bot` (Plan 13-06)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Telegram Login Widget visual | Auth flow | Third-party iframe | Load `/login`, click widget, confirm redirect |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-17 (Wave 1 / Plan 13-01 Task 3)
