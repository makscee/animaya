---
phase: 01-install-foundation
reviewed: 2026-04-13T00:00:00Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - bot/__main__.py
  - bot/main.py
  - run.sh
  - scripts/setup.sh
  - systemd/animaya.service
  - tests/conftest.py
  - tests/test_install.py
  - tests/test_skeleton.py
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-04-13T00:00:00Z
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Summary

Phase 1 skeleton is lean and well-structured. The Python entry point, shell scripts, systemd service, and test suite are all present and consistent. No security vulnerabilities or critical bugs found. Three warnings relate to potential runtime failures (unprotected .env source, missing .env guard in run.sh, and a systemd WorkingDirectory mismatch). Three info items cover minor code quality details.

## Warnings

### WR-01: `run.sh` sources `.env` without existence guard — fails hard if file absent

**File:** `run.sh:13`
**Issue:** `source "$INSTALL_DIR/.env"` runs unconditionally. If `.env` is missing (e.g., first run before `setup.sh`, or a manual deployment), `set -euo pipefail` causes the script to exit with a confusing error rather than a clear message. `setup.sh` creates `.env`, but `run.sh` has no dependency guarantee.
**Fix:**
```bash
if [[ ! -f "$INSTALL_DIR/.env" ]]; then
    echo "ERROR: $INSTALL_DIR/.env not found. Run scripts/setup.sh first." >&2
    exit 1
fi
source "$INSTALL_DIR/.env"
```

### WR-02: `setup.sh` writes raw token values into `.env` without quoting — breaks tokens containing special characters

**File:** `scripts/setup.sh:34-38`
**Issue:** The heredoc writes `TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN` without quoting the value. If a token contains shell-special characters (`:`, `=`, `#`, `!`, spaces), the resulting `.env` file will be malformed and silently produce wrong values when sourced.
**Fix:**
```bash
cat > "$INSTALL_DIR/.env" <<EOF
TELEGRAM_BOT_TOKEN='${TELEGRAM_BOT_TOKEN}'
CLAUDE_CODE_OAUTH_TOKEN='${CLAUDE_CODE_OAUTH_TOKEN}'
DATA_PATH=$DATA_DIR
EOF
```
Single-quote the values so they are stored literally and sourced safely by bash.

### WR-03: `systemd/animaya.service` `WorkingDirectory` hardcodes `%h/animaya` but install path is `$HOME` root

**File:** `systemd/animaya.service:7-8`
**Issue:** `WorkingDirectory=%h/animaya` and `ExecStart=%h/animaya/run.sh` assume the repo is cloned into `~/animaya`. `setup.sh` copies the service file from wherever the repo lives (`$INSTALL_DIR`), but does not substitute the actual install path. If the repo is cloned elsewhere (e.g., `~/projects/animaya`), the service will fail to start. `setup.sh` should template the path at install time.
**Fix:** In `setup.sh`, replace the static copy with a `sed` substitution:
```bash
sed "s|%h/animaya|$INSTALL_DIR|g" \
    "$INSTALL_DIR/systemd/animaya.service" > "$SERVICE_FILE"
```
Or use a `.service.template` file and expand it during install.

## Info

### IN-01: `bot/main.py` — `assemble_claude_md` overwrites an existing `CLAUDE.md` on every startup

**File:** `bot/main.py:59`
**Issue:** `claude_md.write_text(...)` unconditionally overwrites the file. In Phase 3 when modules are installed and the file contains merged module prompts, a restart would wipe all module content. Idempotency guard or a read-check should be added before Phase 3.
**Fix:** No action required for Phase 1, but add a `# TODO(phase-3): check existing content before overwriting` comment to make the constraint visible.

### IN-02: `scripts/setup.sh` — `read -rs` for OAuth token does not echo a newline on all terminals

**File:** `scripts/setup.sh:32`
**Issue:** `read -rs -p "Claude OAuth token: "` suppresses echo (correct for secrets), and the script follows with `echo ""` to restore the cursor to a new line. This is correct. Minor note: if the user hits Ctrl-C mid-input, the terminal is left without a newline and the cursor position is broken. This is cosmetic but can confuse users.
**Fix:** Add a `trap 'echo' INT` before the `read` calls to restore the newline on interrupt.

### IN-03: `tests/test_install.py` — `test_setup_sh_pip_install` uses a disjunction that would pass even with an unscoped `pip`

**File:** `tests/test_install.py:31`
**Issue:** The assertion `assert 'pip" install' in setup_sh or '"$VENV/bin/pip"' in setup_sh or "$VENV/bin/pip" in setup_sh` has three alternatives, the last of which (`"$VENV/bin/pip"` — without the leading quote) would match even a bare string like `echo "$VENV/bin/pip install"`. The test intent is to confirm that the venv-scoped pip is used, but the third disjunct is a weaker check. This does not affect current correctness since the script is already correct, but the test could silently pass on a regression.
**Fix:**
```python
assert "$VENV/bin/pip" in setup_sh and "pip install" in setup_sh
```

---

_Reviewed: 2026-04-13T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
