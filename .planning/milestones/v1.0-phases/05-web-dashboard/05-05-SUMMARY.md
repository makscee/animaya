---
plan: 05-05
phase: 05-web-dashboard
title: Modules list, detail, async install/uninstall jobs
status: complete
completed: 2026-04-15
nyquist_compliant: true
nyquist_signed_off: 2026-04-15
nyquist_retroactive: true
---

# Plan 05-05 Summary

## Delivered

DASH-04 + DASH-05:

- `/modules` — available + installed module cards
- `/modules/{name}` — module detail (manifest, conflicts, install/uninstall buttons)
- `/modules/{name}/install` + `/modules/{name}/uninstall` — async job launch
- `/modules/{name}/job/{job_id}` — HTMX-polled job status fragment (running → done | failed)
- Global asyncio lock — second concurrent install returns 409 with conflict toast

Hook pattern: `module_routes.register(app, templates, hub_dir)` called by `build_app`.

## Files

**Created:**
- `bot/dashboard/jobs.py` — asyncio job runner with global lock + rollback classification + events emission
- `bot/dashboard/modules_view.py` — `describe()` + `list_all()` assembling manifest + registry + conflict detection
- `bot/dashboard/module_routes.py` — list, detail, install, uninstall, job status routes
- `bot/dashboard/templates/modules.html`
- `bot/dashboard/templates/module_detail.html`
- `bot/dashboard/templates/_fragments/module_card.html`
- `bot/dashboard/templates/_fragments/module_card_running.html`
- `bot/dashboard/templates/_fragments/module_card_failed.html`
- `bot/dashboard/templates/_fragments/conflict_toast.html`
- `tests/dashboard/test_jobs.py`
- `tests/dashboard/test_modules.py`

## Commits

- `ab02152` test(05-05): failing tests for modules list + jobs + install/uninstall UX
- `487f21c` feat(05-05): asyncio job runner with global lock + rollback classification + events emission
- `24784d2` (templates + fix) rendered module_detail and fragments; bare `<details>` in failed card

## Verification

- All 26 module/jobs tests green (list, detail, install, uninstall, retry, concurrency 409, failure with rollback classification)
- Full dashboard suite: 74/74 passing
- Events emitted: `module.install.started|done|failed`, `module.uninstall.started|done|failed`

## Deviations

1. Bare `<details>` tag required to satisfy test substring match (was `<details style=...>`).
2. Recovery agent completed template creation after the original executor was interrupted mid-templates; no behavioral deviations from plan contract.
