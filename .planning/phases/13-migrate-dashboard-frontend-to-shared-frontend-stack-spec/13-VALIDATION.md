---
phase: 13
slug: migrate-dashboard-frontend-to-shared-frontend-stack-spec
status: draft
nyquist_compliant: false
wave_0_complete: false
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

*Filled by planner. Each task maps to a row with automated command.*

---

## Wave 0 Requirements

- [ ] `dashboard/package.json` — Next.js 16, React 19, Tailwind 4 pinned per spec
- [ ] `playwright.config.ts` — E2E harness for dashboard parity
- [ ] `tests/dashboard/` — parity + auth + SSE fixtures
- [ ] Bun layer in `docker/Dockerfile.bot`

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

**Approval:** pending
