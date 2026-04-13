---
phase: 01-install-foundation
verified: 2026-04-13T19:30:00Z
status: human_needed
score: 12/12 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Run setup.sh on a real Claude Box (LXC) from a fresh git clone with no .env present"
    expected: "Prompts for tokens interactively, creates .env with chmod 600, creates venv, installs deps, creates ~/hub/knowledge/animaya, installs and starts systemd user service — all without error"
    why_human: "Requires a real systemd user session on Linux; cannot simulate loginctl enable-linger or systemctl --user on macOS dev machine"
  - test: "Start the bot with both tokens set and verify it blocks without crashing"
    expected: "python -m bot runs, logs 'Animaya skeleton running — awaiting modules', stays alive, exits cleanly on SIGINT"
    why_human: "Blocking asyncio.Event().wait() behavior and signal handling require a live process"
---

# Phase 1: Install Foundation Verification Report

**Phase Goal:** Working install script + systemd service on a Claude Box
**Verified:** 2026-04-13T19:30:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | setup.sh is executable and passes bash syntax check | VERIFIED | `bash -n scripts/setup.sh` exits 0 |
| 2 | setup.sh handles .env creation (prompts if missing, validates if present) | VERIFIED | Lines 16–41: sources existing .env and validates both tokens; otherwise prompts interactively with `read -rs` for token, writes .env, chmod 600 |
| 3 | setup.sh creates venv and installs deps via pip | VERIFIED | Lines 50–51: `[[ -d "$VENV" ]] || python3 -m venv "$VENV"` + `"$VENV/bin/pip" install -q -e "$INSTALL_DIR"` |
| 4 | setup.sh checks for Node.js and skips install if present | VERIFIED | Lines 44–46: `if ! command -v node &>/dev/null` warns but does not install |
| 5 | setup.sh creates systemd user service and enables linger | VERIFIED | Lines 68–81: cp service file, `loginctl enable-linger`, `systemctl --user daemon-reload/enable/restart` |
| 6 | run.sh unsets CLAUDECODE and CLAUDECODE_EXECUTION_ID before exec | VERIFIED | Lines 7–8: `unset CLAUDECODE` + `unset CLAUDECODE_EXECUTION_ID` before sourcing .env |
| 7 | Systemd unit has Restart=on-failure and journal logging | VERIFIED | `Restart=on-failure`, `StandardOutput=journal`, `StandardError=journal` all present |
| 8 | Bot entry point validates TELEGRAM_BOT_TOKEN and CLAUDE_CODE_OAUTH_TOKEN | VERIFIED | bot/main.py lines 28–31: iterates REQUIRED_ENV_VARS, sys.exit(1) if missing |
| 9 | Bot creates DATA_PATH directory if absent with default ~/hub/knowledge/animaya | VERIFIED | Lines 34–35: `Path(os.environ.get("DATA_PATH", DEFAULT_DATA_PATH))`, `mkdir(parents=True, exist_ok=True)` |
| 10 | Bot writes a stub CLAUDE.md to DATA_PATH on startup | VERIFIED | `assemble_claude_md()` writes `# Animaya` header + module-prompts-start/end markers |
| 11 | Bot blocks indefinitely after startup | VERIFIED | `await asyncio.Event().wait()` at end of main() |
| 12 | Bot exits with code 1 if required env vars are missing | VERIFIED | `sys.exit(1)` for each missing var; confirmed by test_skeleton.py TestEnvValidation |

**Score:** 12/12 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `scripts/setup.sh` | Idempotent install/upgrade script | VERIFIED | 85 lines, passes bash -n, substantive content |
| `run.sh` | Systemd ExecStart wrapper with env sanitization | VERIFIED | 18 lines, unsets CLAUDECODE vars, sources .env, exec python -m bot |
| `systemd/animaya.service` | Systemd user service unit file | VERIFIED | 15 lines, all required directives present |
| `tests/test_install.py` | Tests for install artifacts | VERIFIED | 134 lines, 3 test classes, 20 tests, all pass |
| `bot/__main__.py` | Async entry point | VERIFIED | 8 lines, imports and calls asyncio.run(main()) |
| `bot/main.py` | Skeleton startup | VERIFIED | 69 lines, env validation, data dir, CLAUDE.md stub, blocking loop |
| `tests/test_skeleton.py` | Tests for skeleton bot behavior | VERIFIED | 77 lines, 3 test classes, 9 tests, all pass |
| `tests/conftest.py` | Shared fixtures | VERIFIED | project_root, setup_sh, run_sh, service_file fixtures present |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `scripts/setup.sh` | `systemd/animaya.service` | `cp "$INSTALL_DIR/systemd/animaya.service" "$SERVICE_FILE"` | WIRED | Line 71: pattern `cp.*animaya\.service` confirmed |
| `systemd/animaya.service` | `run.sh` | ExecStart=%h/animaya/run.sh | WIRED | Line 8 of service file matches `ExecStart.*run\.sh` |
| `run.sh` | `bot/__main__.py` | `exec "$INSTALL_DIR/.venv/bin/python" -m bot` | WIRED | Line 17 of run.sh: `exec.*python.*-m bot` confirmed |
| `bot/__main__.py` | `bot/main.py` | `from bot.main import main` | WIRED | Line 6 of __main__.py |

### Data-Flow Trace (Level 4)

Not applicable — Phase 1 artifacts are install scripts, service units, and a blocking stub. No dynamic data rendering.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| setup.sh bash syntax valid | `bash -n scripts/setup.sh` | exit 0 | PASS |
| run.sh bash syntax valid | `bash -n run.sh` | exit 0 | PASS |
| All install tests pass | `pytest tests/test_install.py -q` | 27 passed | PASS |
| All skeleton tests pass | `pytest tests/test_skeleton.py -q` | 9 passed | PASS |
| Combined suite | `pytest tests/test_install.py tests/test_skeleton.py -q` | 36 passed in 0.55s | PASS |
| bot/main.py has zero v1 imports | `grep -c "from bot.bridge\|..."` | 0 | PASS |
| systemd end-to-end on Claude Box | requires live Linux + systemd | — | SKIP (human) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| INST-01 | 01-01, 01-02 | User can install via git clone + setup.sh | SATISFIED | setup.sh is a complete idempotent installer; bot skeleton is the installed service |
| INST-02 | 01-01 | Setup configures venv, deps, systemd service | SATISFIED | setup.sh: venv creation, pip install, cp service file, systemctl enable |
| INST-03 | 01-01 | Animaya runs as systemd unit with auto-restart + log management | SATISFIED | animaya.service: Restart=on-failure, RestartSec=5, StandardOutput=journal |
| INST-04 | 01-01 | Setup sanitizes CLAUDECODE=1 env var | SATISFIED | run.sh: `unset CLAUDECODE` + `unset CLAUDECODE_EXECUTION_ID` before sourcing .env |

All 4 Phase 1 requirement IDs (INST-01 through INST-04) are covered. No orphaned requirements.

### Anti-Patterns Found

None. Scanned scripts/setup.sh, run.sh, bot/main.py, bot/__main__.py for TODO/FIXME, empty returns, hardcoded stubs. The intentional stub in `assemble_claude_md()` writes static CLAUDE.md content — this is documented in SUMMARY.md as "Intentional Phase 1 stub — Phase 3 module system will extend." No blocker patterns found.

### Human Verification Required

#### 1. Full Install on Claude Box

**Test:** On a real Claude Box LXC (Linux with systemd user session), git clone the repo, run `scripts/setup.sh` with no pre-existing .env. Enter valid tokens when prompted.
**Expected:** Script completes without error; `systemctl --user status animaya` shows `active (running)`; `journalctl --user -u animaya` shows "Animaya skeleton running — awaiting modules"
**Why human:** Requires real systemd user daemon + loginctl on Linux. macOS dev machine has no systemd.

#### 2. Bot Lifecycle (Start, Block, Stop)

**Test:** With .env populated, run `python -m bot` directly. Wait 2 seconds. Send SIGINT (Ctrl-C).
**Expected:** Bot logs startup messages, stays running, exits cleanly on interrupt without traceback
**Why human:** Blocking `asyncio.Event().wait()` and signal handling require a live process; can't verify with pytest timeout trick used in test_data_dir_created.

### Gaps Summary

No gaps. All automated checks pass. Phase goal is structurally achieved — the install script, systemd service, and bot skeleton all exist, are substantive, and are wired correctly. Two items require human confirmation on a real Claude Box before the phase can be fully signed off.

---

_Verified: 2026-04-13T19:30:00Z_
_Verifier: Claude (gsd-verifier)_
