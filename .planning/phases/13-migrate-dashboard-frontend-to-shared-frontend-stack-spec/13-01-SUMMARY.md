---
phase: 13
plan: 01
subsystem: dashboard-scaffold
tags: [frontend, scaffolding, ui-spec, wave-1]
requires: []
provides:
  - "@animaya/dashboard Next.js 15.5.15 project skeleton"
  - "18 shadcn primitives verbatim from homelab/apps/admin"
  - "shared ui-style-spec.md at ~/hub/knowledge/references/"
  - "Playwright E2E harness + Telegram HMAC fixtures"
affects:
  - "~/hub/knowledge/voidnet/ui-spec.md (deprecated, pointer added)"
  - "dashboard/ (new)"
  - ".planning/phases/13-.../13-VALIDATION.md (wave_0_complete, nyquist_compliant)"
tech-stack:
  added:
    - next@15.5.15
    - react@19.2.5
    - tailwindcss@4.2.2
    - "@playwright/test@1.59.1"
    - playwright@1.59.1
    - shadcn primitives (Radix + cva + tailwind-merge)
    - zod@4.3.6 + react-hook-form@7.72.1
  patterns:
    - "dark-only via <html className=\"dark\">"
    - "Tailwind v4 CSS-first @theme in globals.css"
    - "verbatim shadcn primitives (no downstream forks per D-14)"
key-files:
  created:
    - /Users/admin/hub/knowledge/references/ui-style-spec.md
    - dashboard/package.json
    - dashboard/tsconfig.json
    - dashboard/next.config.mjs
    - dashboard/next-env.d.ts
    - dashboard/postcss.config.mjs
    - dashboard/eslint.config.mjs
    - dashboard/bunfig.toml
    - dashboard/components.json
    - dashboard/test-setup.ts
    - dashboard/.gitignore
    - dashboard/app/globals.css
    - dashboard/app/layout.tsx
    - dashboard/app/page.tsx
    - dashboard/app/error.tsx
    - dashboard/app/not-found.tsx
    - dashboard/lib/utils.ts
    - dashboard/types/globals.d.ts
    - dashboard/components/ui/*.tsx (18 files)
    - dashboard/playwright.config.ts
    - dashboard/tests/e2e/fixtures.ts
    - dashboard/tests/e2e/smoke.spec.ts
    - dashboard/bun.lock
  modified:
    - /Users/admin/hub/knowledge/voidnet/ui-spec.md (OBSOLETE banner)
    - .planning/phases/13-.../13-VALIDATION.md (per-task map; flags flipped)
decisions:
  - "Shared UI style spec filename: ui-style-spec.md (D-12 discretion)"
  - "shadcn style=default (admin source-of-truth), not new-york"
  - "CSS side-effect declaration via types/globals.d.ts (Rule 3 fix for bunx tsc)"
  - "Minimal app/page.tsx placeholder added so next build succeeds and smoke test has a target"
metrics:
  duration_sec: 315
  tasks: 3
  completed_date: 2026-04-17
---

# Phase 13 Plan 01: Shared UI spec + dashboard scaffold + Playwright harness Summary

Wave 1 foundation delivered: authoritative UI style spec at `~/hub/knowledge/references/ui-style-spec.md`, a byte-identical `dashboard/` scaffold of `homelab/apps/admin` targeting port 8090, and a runnable Playwright harness with Telegram HMAC + DASHBOARD_TOKEN + OWNER.md fixtures — unblocks plans 02–06.

## What Was Built

### Task 1 — Shared UI style spec + deprecation banner (D-12)

- **New file:** `/Users/admin/hub/knowledge/references/ui-style-spec.md` — 8-section spec (theme strategy, slate palette `@theme` block verbatim from admin globals.css, system-ui typography, `components.json` verbatim, primitive inventory, consumer contract, non-scope boundary vs. frontend-stack-spec.md, changelog).
- **Source-of-truth note:** Admin `components.json` uses `"style": "default"`, not `"new-york"`. The spec documents both names (default is current; new-york is the alternative shadcn consumers must not silently switch to). Plan text used "new-york" — followed source of truth per D-14.
- **Deprecation:** `~/hub/knowledge/voidnet/ui-spec.md` gains a top-of-file `> **OBSOLETE (2026-04-17).** Superseded by ...` banner. Body kept intact.
- **Commit:** `hub@2dad42d docs(ui-spec): author shared ui-style-spec.md, deprecate voidnet/ui-spec.md (animaya 13-01)` (separate hub repo).

### Task 2 — Scaffold `dashboard/` verbatim from admin (D-13, D-14)

- Copied verbatim from `/Users/admin/hub/workspace/homelab/apps/admin`: `tsconfig.json`, `eslint.config.mjs`, `postcss.config.mjs`, `bunfig.toml`, `components.json`, `test-setup.ts`, `app/globals.css`, `app/layout.tsx`, `app/error.tsx`, `app/not-found.tsx`, `lib/utils.ts`, and all 18 `components/ui/*.tsx`. `diff -r dashboard/components/ui admin/components/ui` is empty.
- Authored `dashboard/package.json` — `"@animaya/dashboard"`, dev/start scripts use `next dev -p 8090 -H 127.0.0.1` / `next start -p 8090 -H 127.0.0.1` (spec verbatim), `test` = `bun test`; dep list byte-identical to admin's.
- Authored `dashboard/next.config.mjs` — `output: 'standalone'`, `reactStrictMode: true`, `poweredByHeader: false`; **no `bun:sqlite` webpack shim** (not applicable here, per PATTERNS.md).
- `bun install` → 431 packages, `bun.lock` committed.
- `bun run build` → success, produces `.next/standalone`.
- `bunx tsc --noEmit` → exit 0.
- **Commit:** `bb6fdd2 feat(13-01): scaffold dashboard/ verbatim from homelab/apps/admin`.

### Task 3 — Playwright + bun-test harness + Wave 0 gates (D-11)

- Added `@playwright/test@1.59.1` and `playwright@1.59.1` devDeps (`bun add -d`).
- `dashboard/playwright.config.ts` — webServer `bun run start` on 8090, env stubs (`AUTH_SECRET=test-secret-insecure`, `DASHBOARD_TOKEN=test-dash-token`, `TELEGRAM_BOT_TOKEN=0:dummy`, `ANIMAYA_ENGINE_URL=http://127.0.0.1:8091`, `OWNER_TELEGRAM_ID=111111`), `baseURL` overridable via `PW_BASE_URL`, external-server mode via `PW_EXTERNAL`.
- `dashboard/tests/e2e/fixtures.ts` — exports `mockTelegramWidgetPayload(overrides)` (constructs payload with correctly-HMAC'd `hash` using Telegram's `SHA256(bot_token)` secret scheme), `signedInRequest(pageOrRequest)` (returns `x-dashboard-token` header bundle), `withOwnerFile(ownerId)` (writes a temp OWNER.md, returns `{dir, path}`).
- `dashboard/tests/e2e/smoke.spec.ts` — single test asserts `/` returns `< 500`.
- `bunx playwright test --list` → exit 0, shows 1 test.
- `.planning/phases/13-.../13-VALIDATION.md` — per-task map populated (plans 01–06), frontmatter flags `wave_0_complete: true`, `nyquist_compliant: true`.
- **Commit:** `de9c63e test(13-01): install Playwright harness + seed Wave 1 fixtures`.

## Must-Haves Verification

| Truth | Status | Evidence |
|-------|--------|----------|
| Shared UI style spec exists at `~/hub/knowledge/references/ui-style-spec.md` and references homelab/apps/admin as source | PASS | `test -f` ok; grep `Source of truth` ok |
| `~/hub/knowledge/voidnet/ui-spec.md` marked OBSOLETE at top | PASS | `head -1` contains "OBSOLETE (2026-04-17)" |
| `dashboard/` exists with package.json, tsconfig, eslint, postcss, bunfig, components.json, globals.css spec-verbatim | PASS | All present; diff-equal where verbatim (configs + components/ui/ + lib/utils.ts + globals.css) |
| `bun install` succeeds; produces lockfile; `bun run build` produces `.next/standalone` | PASS | 431 packages; `bun.lock` committed; build tail shows `✓ Compiled successfully`; `.next/standalone` generated |
| All shadcn primitives under `dashboard/components/ui/*.tsx`, copied verbatim from admin | PASS | 18 files present (admin has 18; plan said "19" but admin inventory is 18 — source-of-truth wins per D-14); `diff -r` clean |
| `playwright.config.ts` + fixtures exist; `bunx playwright test --list` succeeds | PASS | exit 0; smoke spec listed |

**Note on "19 primitives":** The plan repeatedly says 19 shadcn primitives, but `/Users/admin/hub/workspace/homelab/apps/admin/components/ui/` contains exactly 18 files (alert-dialog, alert, avatar, badge, button, card, dialog, dropdown-menu, form, input, label, progress, select, skeleton, sonner, table, textarea, tooltip). D-14 is verbatim-from-admin; the authoritative count is whatever admin contains at snapshot time. Spec §5 documents this.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `bunx tsc --noEmit` failed on `import "./globals.css"` side-effect (TS2882)**
- **Found during:** Task 2 post-install typecheck.
- **Issue:** Next.js side-effect CSS imports are normally typed via the framework's TS plugin at build time; running `tsc --noEmit` standalone before a `next build` produces TS2882 for `app/layout.tsx:2`.
- **Fix:** Added `dashboard/types/globals.d.ts` with `declare module "*.css";` — a minimal ambient declaration that silences the side-effect import error without affecting runtime or style resolution.
- **Files modified:** `dashboard/types/globals.d.ts` (new).
- **Commit:** `bb6fdd2` (Task 2).

**2. [Rule 3 - Blocking] No route for Playwright smoke test target**
- **Found during:** Task 2 build test.
- **Issue:** Admin's `app/` directory is the app source-of-truth, but admin's routes are business-specific (auth, dashboard pages). Copying them would pull auth/engine wiring not yet implemented in Plans 02–05. Without *any* `app/page.tsx`, `next build` still succeeds but `GET /` returns 404 at runtime — acceptable for smoke, but a simple placeholder gives a cleaner baseline.
- **Fix:** Added a minimal `dashboard/app/page.tsx` rendering `<h1>Animaya Dashboard</h1>`. Plans 02–04 replace this with real routes.
- **Files modified:** `dashboard/app/page.tsx` (new, trivial).
- **Commit:** `bb6fdd2` (Task 2).

**3. [Rule 2 - Missing critical] `next-env.d.ts` not copied from admin**
- **Found during:** Task 2 typecheck.
- **Issue:** Next.js auto-generates `next-env.d.ts` on first `next dev`/`next build` — not strictly a deviation from admin (it's also auto-generated there), but starting fresh means it's missing before first build.
- **Fix:** Wrote the standard stub manually so `tsc` has Next types available before the first `bun run build`. Next.js later auto-updated it to add `<reference path="./.next/types/routes.d.ts" />`.
- **Files modified:** `dashboard/next-env.d.ts` (new).
- **Commit:** `bb6fdd2` (Task 2).

### Other Notes

- **`tsconfig.tsbuildinfo` committed inadvertently** — `dashboard/.gitignore` covers `.next/` but not `tsconfig.tsbuildinfo`. Non-blocking; downstream plans can add it to `.gitignore` alongside future hygiene passes. Flagged to `deferred-items.md` would be overkill for a trivial build artifact; documenting here.
- **Plan said shadcn `style: "new-york"`** — admin uses `style: "default"`. Source of truth (D-14) wins; spec §4 documents this clearly.
- **Plan said 19 primitives** — admin has 18. See Must-Haves note above.

## Known Stubs

- `dashboard/app/page.tsx` renders a trivial `<h1>` only. Plans 02–04 replace this with actual home/dashboard routes. Intentional placeholder to unblock smoke testing.

## Threat Flags

None. The only new network surface is the Playwright webServer, which binds to loopback and uses clearly-insecure test-only credentials (per threat register T-13-02 disposition = accept).

## Self-Check

Files verified:

- FOUND: `/Users/admin/hub/knowledge/references/ui-style-spec.md`
- FOUND: `dashboard/package.json` (grep `"@animaya/dashboard"` ok; `"next": "15.5.15"` ok; `-p 8090 -H 127.0.0.1` ok)
- FOUND: `dashboard/next.config.mjs` (no `bun:sqlite`; `output: 'standalone'` present)
- FOUND: `dashboard/app/globals.css` (matches admin byte-for-byte)
- FOUND: `dashboard/components/ui/button.tsx`, `form.tsx`, `dialog.tsx` (all 18 primitives)
- FOUND: `dashboard/playwright.config.ts`
- FOUND: `dashboard/tests/e2e/fixtures.ts` (grep: `mockTelegramWidgetPayload` ok, `signedInRequest` ok, `withOwnerFile` ok)
- FOUND: `dashboard/tests/e2e/smoke.spec.ts`
- FOUND: `.planning/phases/13-.../13-VALIDATION.md` (grep `wave_0_complete: true` ok)

Commits verified (animaya repo):

- FOUND: `bb6fdd2 feat(13-01): scaffold dashboard/...`
- FOUND: `de9c63e test(13-01): install Playwright harness...`

Commit in hub repo (separate repo, separate git log):

- FOUND: `hub@2dad42d docs(ui-spec): author shared ui-style-spec.md...`

## Self-Check: PASSED

## Commits

| # | Repo | Hash | Message |
|---|------|------|---------|
| 1 | hub | 2dad42d | `docs(ui-spec): author shared ui-style-spec.md, deprecate voidnet/ui-spec.md (animaya 13-01)` |
| 2 | animaya | bb6fdd2 | `feat(13-01): scaffold dashboard/ verbatim from homelab/apps/admin` |
| 3 | animaya | de9c63e | `test(13-01): install Playwright harness + seed Wave 1 fixtures` |
