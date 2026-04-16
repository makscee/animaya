---
phase: quick-260416-fzf
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - bot/dashboard/deps.py
  - tests/dashboard/test_auth.py
autonomous: true
requirements:
  - QUICK-260416-fzf

must_haves:
  truths:
    - "After owner claim, a browser with a pre-claim bootstrap cookie (user_id=0) hitting a protected route receives a 302 to /login, not a 403."
    - "A genuine non-owner (valid cookie with user_id != 0 and != owner_id) still receives 403."
    - "The 'no owner claimed yet' branch still returns 0 (open bootstrap)."
    - "The 'no cookie / invalid cookie' branch still redirects 302 to /login."
    - "Owner with valid cookie matching owner_id still gets 200."
  artifacts:
    - path: "bot/dashboard/deps.py"
      provides: "require_owner with stale-bootstrap 302 branch before the 403"
      contains: "user_id == 0"
    - path: "tests/dashboard/test_auth.py"
      provides: "Test covering stale bootstrap cookie → 302"
      contains: "stale_bootstrap"
  key_links:
    - from: "bot/dashboard/deps.py::require_owner"
      to: "HTTPException(status_code=302, Location=/login)"
      via: "user_id == 0 check BEFORE the user_id != owner_id 403 branch"
      pattern: "user_id == 0"
---

<objective>
Fix `require_owner` so a stale open-bootstrap cookie (user_id=0, minted before owner
claim) yields a 302 redirect to /login instead of a 403 "Not the bot owner" once an
owner has claimed. Today the browser hits a 403 error page with no auto-recovery;
after this fix the browser auto-redirects to /login, where the operator re-hits the
pairing token URL to mint a fresh cookie bound to the real owner_id.

Purpose: Eliminate the dead-end 403 for the legitimate operator whose first dashboard
session was minted under open-bootstrap (pre-claim sentinel cookie), while keeping
403 for real non-owner sessions.

Output: One-branch change in `bot/dashboard/deps.py` plus a new regression test in
`tests/dashboard/test_auth.py`.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@bot/dashboard/deps.py
@bot/dashboard/auth.py
@tests/dashboard/test_auth.py

<interfaces>
<!-- Key contracts the executor needs. Extracted from files above. -->

From bot/dashboard/deps.py (current):
```python
def require_owner(
    request: Request,
    session: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> int:
    hub_dir: Path = request.app.state.hub_dir
    owner_id = _get_owner_id(hub_dir)
    if owner_id is None:
        return 0  # open access -- no owner claimed yet
    if session is None:
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    payload = read_session_cookie(session)
    if payload is None:
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    user_id = int(payload["user_id"])
    if user_id != owner_id:
        raise HTTPException(status_code=403, detail="Not the bot owner")   # ← split this
    return user_id
```

From bot/dashboard/auth.py:
```python
def issue_session_cookie(user_id: int, auth_date: int = 0, hash_: str = "") -> str
def read_session_cookie(token: str | None, max_age: int = SESSION_MAX_AGE_SECONDS) -> dict | None
```

From tests/dashboard/test_auth.py (existing test shape — mirror this style):
- `_stub_app(temp_hub_dir)` builds a FastAPI app with `/who` route using `require_owner`.
- Existing tests: `test_require_owner_no_cookie_redirects`, `test_require_owner_bad_cookie_redirects`,
  `test_require_owner_valid_non_owner_403`, `test_require_owner_valid_owner_passes`,
  `test_require_owner_open_bootstrap_no_owner`.
- Fixtures: `session_secret`, `owner_id`, `temp_hub_dir` (from conftest; temp_hub_dir
  seeds state.json with claimed owner_id=111222333 in most tests).
- `issue_session_cookie(user_id, auth_date, hash_)` used to mint test cookies.
- `TestClient(app, follow_redirects=False)` pattern; redirects asserted via
  `r.status_code == 302` and `r.headers["location"] == "/login"`.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add stale-bootstrap 302 branch + regression test</name>
  <files>bot/dashboard/deps.py, tests/dashboard/test_auth.py</files>
  <behavior>
    New test in tests/dashboard/test_auth.py, placed next to the existing
    `test_require_owner_*` tests (after `test_require_owner_valid_non_owner_403`,
    before `test_require_owner_valid_owner_passes` is fine):

    ```python
    def test_require_owner_stale_bootstrap_cookie_redirects(
        session_secret: str, owner_id: int, temp_hub_dir: Path
    ) -> None:
        """Valid cookie with user_id=0 (pre-claim bootstrap sentinel) + claimed owner
        → 302 redirect to /login, NOT 403. Operator re-hits pairing token URL to mint
        a fresh cookie bound to real owner_id."""
        from bot.dashboard.auth import issue_session_cookie

        cookie = issue_session_cookie(0, 1700000000, "bootstrap")
        app = _stub_app(temp_hub_dir)
        client = TestClient(app, follow_redirects=False)
        r = client.get("/who", cookies={"animaya_session": cookie})
        assert r.status_code == 302
        assert r.headers["location"] == "/login"
    ```

    This test MUST fail against the current deps.py (current code returns 403 for
    user_id=0) and MUST pass after the code change in this task.

    Existing tests MUST continue to pass unchanged:
    - `test_require_owner_no_cookie_redirects` — still 302 (no cookie)
    - `test_require_owner_bad_cookie_redirects` — still 302 (invalid cookie)
    - `test_require_owner_valid_non_owner_403` — still 403 (user_id=999, not 0)
    - `test_require_owner_valid_owner_passes` — still 200
    - `test_require_owner_open_bootstrap_no_owner` — still 200 user_id=0 (no state.json owner)
  </behavior>
  <action>
    RED→GREEN in two steps, single task, single commit is fine (quick task scope).

    Step 1 — write the failing test first:
    Add `test_require_owner_stale_bootstrap_cookie_redirects` to
    `tests/dashboard/test_auth.py` as specified in <behavior>. Run it and confirm it
    fails with 403 (proves the bug exists).

    Step 2 — fix `bot/dashboard/deps.py::require_owner`:
    Replace the final branch:

    ```python
        user_id = int(payload["user_id"])
        if user_id != owner_id:
            raise HTTPException(status_code=403, detail="Not the bot owner")
        return user_id
    ```

    with:

    ```python
        user_id = int(payload["user_id"])
        if user_id == 0:
            # Stale open-bootstrap cookie (minted pre-claim). Not an attacker —
            # legitimate operator whose session predates the owner claim. Send them
            # back through /login to mint a fresh cookie bound to the real owner_id.
            raise HTTPException(status_code=302, headers={"Location": "/login"})
        if user_id != owner_id:
            raise HTTPException(status_code=403, detail="Not the bot owner")
        return user_id
    ```

    Also update the docstring `Raises:` block to add the stale-bootstrap case, e.g.:

    ```
        HTTPException(302, Location=/login): no cookie, invalid cookie, OR stale
            open-bootstrap cookie (user_id=0) after owner has claimed.
        HTTPException(403): cookie valid with user_id != 0 but does not match
            state.json owner_id (real non-owner).
    ```

    Ordering matters: the `user_id == 0` check MUST come before the `!= owner_id`
    check, otherwise 0 still falls through to 403.

    Out of scope (do NOT touch):
    - Cookie TTL, SESSION_MAX_AGE_SECONDS, session secret handling.
    - The claim flow, /login route, pairing code issuance.
    - "Make auth more persistent" concerns — separate task.

    Re-run the full dashboard test file and confirm all six `test_require_owner_*`
    tests pass plus the new one.
  </action>
  <verify>
    <automated>python -m pytest tests/dashboard/test_auth.py -v</automated>
  </verify>
  <done>
    - `tests/dashboard/test_auth.py::test_require_owner_stale_bootstrap_cookie_redirects` passes.
    - All pre-existing `test_require_owner_*` tests still pass unchanged.
    - `bot/dashboard/deps.py::require_owner` has a `user_id == 0` branch raising
      `HTTPException(status_code=302, headers={"Location": "/login"})` placed BEFORE
      the `user_id != owner_id` 403 branch.
    - Docstring updated to document the stale-bootstrap 302 case.
  </done>
</task>

</tasks>

<verification>
Run the dashboard auth test file:

```bash
python -m pytest tests/dashboard/test_auth.py -v
```

All tests pass, including the new `test_require_owner_stale_bootstrap_cookie_redirects`.

Sanity-check the rest of the dashboard tests aren't disturbed:

```bash
python -m pytest tests/dashboard/ -v
```

Should stay green (no other test relies on 403 for user_id=0 — grep confirmed only
test_auth.py references `user_id=0` semantics directly).
</verification>

<success_criteria>
- A browser cookie minted pre-claim (user_id=0) receives 302 → /login on any protected
  route after the owner has claimed, causing automatic redirect in the browser.
- Real non-owner sessions (valid cookie, user_id ∉ {0, owner_id}) still receive 403.
- No other behaviour changes: no-cookie/invalid-cookie still 302; no-owner-claimed
  still returns 0; valid-owner still returns owner_id.
- Full `tests/dashboard/test_auth.py` suite green; no other test files modified.
</success_criteria>

<output>
After completion, create `.planning/quick/260416-fzf-redirect-stale-bootstrap-cookie-to-login/260416-fzf-SUMMARY.md`
documenting the one-line behavioural change and the new test.
</output>
