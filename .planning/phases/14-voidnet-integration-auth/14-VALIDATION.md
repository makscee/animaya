---
phase: 14
slug: voidnet-integration-auth
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-22
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `bun:test` (unit) + `@playwright/test` (E2E) |
| **Config file** | `dashboard/bunfig.toml`, `dashboard/playwright.config.ts` |
| **Quick run command** | `cd dashboard && bun test lib/voidnet-auth.server.test.ts` |
| **Full suite command** | `cd dashboard && bun test && bun run playwright test` |
| **Estimated runtime** | ~30s unit + ~60s E2E |

---

## Sampling Rate

- **After every task commit:** Run the quick command for the module under change
- **After every plan wave:** Run the full unit suite (`bun test`)
- **Before `/gsd-verify-work`:** Full unit + E2E suite must be green
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

*Planner fills during PLAN.md generation. Each task references its REQ-ID from SPEC.md and an automated command.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | REQ-01..REQ-08 (from SPEC) | T-14-01 replay, T-14-02 sig forge, T-14-03 owner mismatch | — | unit/E2E | TBD | ❌ W0 | ⬜ pending |

---

## Wave 0 Requirements

- [ ] `dashboard/lib/voidnet-auth.server.test.ts` — verifier unit test stubs (signature, timestamp, handle regex, owner check)
- [ ] `dashboard/tests/voidnet-middleware.spec.ts` — Playwright E2E stubs (valid sig → passes, bad sig → 401 JSON, no headers → Telegram flow, owner mismatch → 403)
- [ ] Hand-computed HMAC test vector fixture (mirror `telegram-widget.server.test.ts` cross-verified vector pattern)
- [ ] Minted-JWT decode smoke test — middleware `encode()` output round-trips through `getToken()` with same `AUTH_SECRET` + cookie salt

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live voidnet-api proxy integration | REQ-01..REQ-07 end-to-end | Requires running voidnet-api instance, out-of-repo | Deploy to staging LXC with `VOIDNET_HMAC_SECRET` set; hit dashboard through voidnet proxy; confirm no Telegram widget appears and session is active |
| Doc env contract | REQ-08 | Prose correctness check | Grep `dashboard/DASHBOARD.md` or `README.md` for `VOIDNET_HMAC_SECRET` and `OWNER_TELEGRAM_ID` pairing section |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (verifier, middleware, E2E, fixtures)
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter after planner fills per-task map

**Approval:** pending
