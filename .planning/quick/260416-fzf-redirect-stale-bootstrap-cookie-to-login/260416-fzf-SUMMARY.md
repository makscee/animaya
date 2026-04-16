---
task: 260416-fzf
type: quick
title: Redirect stale bootstrap cookie to login instead of 403
completed: 2026-04-16
commit: cf865a1
---

# 260416-fzf: Redirect Stale Bootstrap Cookie To Login

## Description

When a dashboard operator logged in during open-bootstrap (no owner yet
claimed), `bot.dashboard.auth` minted a session cookie with `user_id=0`.
After the owner subsequently claimed via `/login`, any request the operator
made with their pre-claim cookie hit `require_owner`'s `user_id != owner_id`
branch and returned a 403 — wedging the legitimate owner out of the
dashboard with no clear recovery path.

Fix: added a dedicated `user_id == 0` branch in `require_owner` that
raises a 302 redirect to `/login`, so stale bootstrap cookies are sent
through the normal sign-in flow to mint a fresh cookie bound to the real
`owner_id` from `state.json`. Real non-owners (valid cookie, non-zero
user_id mismatched against state) still receive 403 as before.

## Files Modified

- `bot/dashboard/deps.py` — New `user_id == 0` branch in `require_owner`
  raises `HTTPException(302, Location=/login)` before the existing
  `user_id != owner_id` 403 branch. Docstring updated to describe the
  stale-bootstrap redirect case.
- `tests/dashboard/test_auth.py` — Added
  `test_require_owner_stale_bootstrap_cookie_redirects_to_login`
  exercising the stale-cookie scenario (cookie minted with `user_id=0`,
  `state.json` owner claimed). Asserts 302 with `Location: /login` (not
  403). Fixed import ordering for ruff I001.

## Test Evidence

- `uvx ruff check bot/dashboard/deps.py tests/dashboard/test_auth.py`
  → `All checks passed!`
- `pytest tests/dashboard/test_auth.py` → 13 passed (including the new
  stale-bootstrap redirect test).

## Commit

`cf865a1` — `fix(quick-260416-fzf): redirect stale bootstrap cookie to login instead of 403`
