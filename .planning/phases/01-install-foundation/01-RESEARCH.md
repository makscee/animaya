# Phase 1: Install & Foundation - Research

**Researched:** 2026-04-13
**Domain:** Python systemd service install, shell scripting, LXC-native deployment
**Confidence:** HIGH

## Summary

Phase 1 installs Animaya on a Claude Box (Proxmox LXC with Claude Code) via `git clone` + `setup.sh`, creates a Python venv, writes a systemd unit, and produces a running skeleton service. All user decisions are locked in CONTEXT.md. The work is pure shell + Python scaffolding with no new library dependencies.

The CLAUDECODE=1 sanitization (INST-04) is the most subtle requirement — it must be cleared in `run.sh` before `python -m bot` executes, otherwise the Claude Code SDK subprocess detects it and may alter its behavior or hang. This is handled in the wrapper script, not in systemd's Environment= directive, because env files sourced by systemd can reintroduce it.

**Primary recommendation:** Build setup.sh as a single idempotent script; use run.sh as the systemd ExecStart wrapper; keep the skeleton bot entry point minimal — just env validation, CLAUDE.md assembler stub, and a blocking sleep loop.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01: setup.sh checks for `.env` — if present validates required vars; if missing prompts interactively, then writes `.env`
- D-02: Python venv in project directory (`~/animaya/.venv`)
- D-03: setup.sh checks for Node.js and installs if missing
- D-04: Systemd ExecStart uses a wrapper `run.sh` (activates venv, sources env, runs bot)
- D-05: Application code installs to `~/animaya` (no root required)
- D-06: Module data at `~/hub/knowledge/animaya/` — git-versioned with Hub
- D-07: Updates via `git pull` + re-run `setup.sh` (idempotent)
- D-09: Freshly installed service runs module loader skeleton + CLAUDE.md assembler with empty module list
- D-10: No user-facing behavior at Phase 1 (no CLI, no health endpoint, no network listeners)

### Claude's Discretion
- D-08: Migration handling — decide whether inline in setup.sh or separate step
- Uninstall path — decide whether `setup.sh --uninstall` belongs in Phase 1 or deferred

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INST-01 | User can install via `git clone` + `setup.sh` | setup.sh pattern documented below |
| INST-02 | Setup configures Python venv, installs deps, creates systemd service | venv + pip install + systemctl enable pattern |
| INST-03 | Animaya runs as systemd unit with auto-restart and log management | systemd unit file pattern with Restart=on-failure |
| INST-04 | Setup sanitizes CLAUDECODE=1 env var | `unset CLAUDECODE` in run.sh before exec |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python venv | stdlib | Dependency isolation | No root, no conflicts with system Python or Claude Code packages |
| pip | bundled | Package install from pyproject.toml | Standard; `pip install -e .` reads existing pyproject.toml |
| systemd | OS-provided | Service lifecycle, auto-restart, journald logging | Native to LXC; no extra tooling needed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| bash | OS-provided | setup.sh + run.sh | Universally available on LXC |

No new Python packages needed for Phase 1 skeleton. Existing `pyproject.toml` dependencies are sufficient; Phase 1 skeleton does not exercise Telegram or Claude SDK paths.

**Installation (Phase 1 skeleton):**
```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

[VERIFIED: pyproject.toml in codebase — all deps already declared]

## Architecture Patterns

### File Layout After Install
```
~/animaya/
├── bot/                   # Python package (existing)
│   ├── __main__.py        # Entry point: python -m bot
│   └── main.py            # Startup sequence (reference)
├── .venv/                 # Created by setup.sh (gitignored)
├── .env                   # Created by setup.sh (gitignored)
├── run.sh                 # Wrapper for systemd ExecStart
├── setup.sh               # Idempotent install/upgrade script
└── pyproject.toml         # Deps + ruff + pytest config

~/hub/knowledge/animaya/   # Module data (D-06)
```

### Pattern 1: Idempotent setup.sh

**What:** Single script handles both fresh install and upgrade. Detects existing state and skips completed steps.
**When to use:** Always — user re-runs same script for upgrades (D-07).

```bash
# Source: shell scripting best practice [ASSUMED]
set -euo pipefail

INSTALL_DIR="$HOME/animaya"
VENV="$INSTALL_DIR/.venv"
SERVICE="animaya"

# --- Env file ---
if [[ -f "$INSTALL_DIR/.env" ]]; then
    # Validate required vars present
    source "$INSTALL_DIR/.env"
    [[ -z "${TELEGRAM_BOT_TOKEN:-}" ]] && echo "ERROR: TELEGRAM_BOT_TOKEN missing in .env" && exit 1
    [[ -z "${CLAUDE_CODE_OAUTH_TOKEN:-}" ]] && echo "ERROR: CLAUDE_CODE_OAUTH_TOKEN missing in .env" && exit 1
else
    read -rp "Telegram bot token: " TELEGRAM_BOT_TOKEN
    read -rp "Claude OAuth token: " CLAUDE_CODE_OAUTH_TOKEN
    cat > "$INSTALL_DIR/.env" <<EOF
TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN
CLAUDE_CODE_OAUTH_TOKEN=$CLAUDE_CODE_OAUTH_TOKEN
DATA_PATH=$HOME/hub/knowledge/animaya
EOF
fi

# --- Venv ---
[[ -d "$VENV" ]] || python3 -m venv "$VENV"
"$VENV/bin/pip" install -q -e "$INSTALL_DIR/.[dev]"

# --- Hub knowledge dir ---
mkdir -p "$HOME/hub/knowledge/animaya"

# --- Systemd (user mode, no root) ---
systemctl --user enable --now "$SERVICE" 2>/dev/null || true
```

### Pattern 2: run.sh Wrapper (INST-04 critical)

**What:** Wrapper script that clears CLAUDECODE=1 before launching Python, so the Claude Code SDK subprocess doesn't inherit it.
**Why:** When Animaya itself runs inside a Claude Code session (e.g., during development), `CLAUDECODE=1` is set in the environment. The SDK detects this and may alter behavior or refuse to spawn sub-processes. Clearing it in run.sh ensures the production service always starts clean.

```bash
#!/usr/bin/env bash
# run.sh — systemd ExecStart wrapper
set -euo pipefail

INSTALL_DIR="$(cd "$(dirname "$0")" && pwd)"

# Source env vars
set -a
source "$INSTALL_DIR/.env"
set +a

# INST-04: Clear CLAUDECODE to prevent SDK subprocess hang
unset CLAUDECODE
unset CLAUDECODE_EXECUTION_ID  # also clear related vars if present

# Activate venv and run
source "$INSTALL_DIR/.venv/bin/activate"
exec python -m bot
```

[ASSUMED — pattern derived from systemd + venv best practices; unset behavior confirmed by bash docs]

### Pattern 3: Systemd User Service (no root)

**What:** `~/.config/systemd/user/animaya.service` — runs as the current user, survives reboot via `loginctl enable-linger`.
**When to use:** D-05 mandates no root. Systemd user mode is the correct approach.

```ini
# Source: systemd.service(5) man page [ASSUMED - standard systemd syntax]
[Unit]
Description=Animaya AI Assistant
After=network.target

[Service]
Type=simple
WorkingDirectory=%h/animaya
ExecStart=%h/animaya/run.sh
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=animaya

[Install]
WantedBy=default.target
```

**Enable linger** so service starts on boot without user login:
```bash
loginctl enable-linger "$USER"
systemctl --user daemon-reload
systemctl --user enable --now animaya
```

[ASSUMED — standard systemd user service pattern; loginctl linger is the established solution for user services that must survive logout]

### Pattern 4: Phase 1 Skeleton Bot Entry Point

Since D-10 mandates no user-facing behavior, the skeleton `__main__.py` should:
1. Validate env vars (TELEGRAM_BOT_TOKEN, CLAUDE_CODE_OAUTH_TOKEN) — exit(1) on missing
2. Create `DATA_PATH` directory if absent
3. Run CLAUDE.md assembler stub (empty module list → writes base CLAUDE.md only)
4. Log "Animaya skeleton running" and block (e.g., `asyncio.get_event_loop().run_forever()`)

This satisfies Phase 1 success criteria and gives Phase 2 a clean plug-in point for the Telegram bridge.

### Anti-Patterns to Avoid
- **Root-required setup:** Using `sudo systemctl` instead of `systemctl --user` — violates D-05
- **Hardcoded paths:** Using `/opt/animaya` (old Docker pattern from deploy.sh) — use `$HOME/animaya`
- **Sourcing .env in systemd EnvironmentFile=:** If .env contains `CLAUDECODE=1`, systemd will pass it through. Use run.sh instead (D-04 rationale)
- **pip install without venv:** Would conflict with system Python packages on Claude Box
- **`python -m bot` before venv is active:** Will import wrong packages or fail to find claude-code-sdk

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Service auto-restart | Custom watchdog loop | systemd `Restart=on-failure` | Handles crash, OOM, signal; journald integration free |
| Log rotation | Custom file rotation | journald (automatic via StandardOutput=journal) | journalctl -u animaya works out of box; no logrotate config needed |
| Env var loading | Custom parser | `set -a; source .env; set +a` in run.sh | Handles quoting, comments; no extra library |
| Linger on boot | cron @reboot | `loginctl enable-linger` | Proper systemd integration; survives multi-user scenarios |

## Common Pitfalls

### Pitfall 1: CLAUDECODE=1 Inheritance
**What goes wrong:** Service is started from a Claude Code session during development. CLAUDECODE=1 propagates into run.sh → Python process. SDK detects it and hangs or refuses to operate.
**Why it happens:** Environment vars are inherited by child processes unless explicitly unset.
**How to avoid:** `unset CLAUDECODE` as the first action in run.sh, before sourcing .env (which might also contain it).
**Warning signs:** Service starts but immediately stalls with no log output.

### Pitfall 2: Venv Not Activated Before pip install -e
**What goes wrong:** `pip install -e .` installs into system Python instead of venv.
**Why it happens:** Forgetting to call `.venv/bin/pip` explicitly (or activating first).
**How to avoid:** Always use `"$VENV/bin/pip"` in setup.sh — never rely on PATH.

### Pitfall 3: Systemd User Service Doesn't Start on Boot
**What goes wrong:** Service works when user is logged in, dies after logout / doesn't start on reboot.
**Why it happens:** Systemd user instances only run while a user session is active by default.
**How to avoid:** `loginctl enable-linger "$USER"` — run once during setup.sh.

### Pitfall 4: setup.sh Not Idempotent on Re-run
**What goes wrong:** Re-running setup.sh (for upgrade) recreates venv, loses installed packages, or prompts for tokens again even if .env exists.
**Why it happens:** Missing existence checks (`[[ -d "$VENV" ]] || ...`).
**How to avoid:** Guard every action with an existence check. Test by running setup.sh twice on a fresh install.

### Pitfall 5: Node.js Check Interfering with Claude Code
**What goes wrong:** setup.sh installs Node.js via apt/nvm and overwrites the Node.js that Claude Code CLI depends on.
**Why it happens:** D-03 says "install if missing" but Claude Box already has Node.js for Claude Code.
**How to avoid:** Check with `command -v node` first. If found, skip install entirely. Only install if absent.
**Warning signs:** Claude Code CLI stops working after setup.sh runs.

### Pitfall 6: DATA_PATH vs Hub Path Mismatch
**What goes wrong:** Bot defaults to `/data` (old Docker path from main.py line 32) but D-06 sets `DATA_PATH=~/hub/knowledge/animaya`.
**Why it happens:** Existing `main.py` has `Path(os.environ.get("DATA_PATH", "/data"))`.
**How to avoid:** setup.sh must write `DATA_PATH=$HOME/hub/knowledge/animaya` into .env. The default `/data` is the Docker path and does not exist on LXC.

## Code Examples

### Verified Entry Point Pattern (from existing codebase)
```python
# Source: bot/main.py (existing)
import os, sys, logging
from pathlib import Path

logger = logging.getLogger(__name__)

def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not set")
        sys.exit(1)
    if not os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
        logger.error("CLAUDE_CODE_OAUTH_TOKEN not set")
        sys.exit(1)
    data_path = Path(os.environ.get("DATA_PATH", "/data"))
    data_path.mkdir(parents=True, exist_ok=True)
```
[VERIFIED: bot/main.py in codebase]

### Phase 1 Skeleton Main (new pattern)
```python
# Source: derived from bot/main.py pattern [ASSUMED - new code]
import asyncio, logging, os, sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

async def main() -> None:
    # Env validation
    for var in ("TELEGRAM_BOT_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN"):
        if not os.environ.get(var):
            logger.error("%s not set", var)
            sys.exit(1)

    # Data dir
    data_path = Path(os.environ.get("DATA_PATH", str(Path.home() / "hub/knowledge/animaya")))
    data_path.mkdir(parents=True, exist_ok=True)
    logger.info("Data path: %s", data_path)

    # CLAUDE.md assembler stub (Phase 2+ will register modules here)
    _assemble_claude_md(data_path)
    logger.info("Animaya skeleton running — awaiting modules")

    # Block until shutdown
    await asyncio.Event().wait()

def _assemble_claude_md(data_path: Path) -> None:
    """Stub: write base CLAUDE.md with empty module list."""
    claude_md = data_path / "CLAUDE.md"
    claude_md.write_text("# Animaya\n\n<!-- modules will be injected here -->\n")
    logger.info("CLAUDE.md written to %s", claude_md)

if __name__ == "__main__":
    asyncio.run(main())
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Docker-based deploy (scripts/deploy.sh) | LXC-native systemd service | This project (v2) | No Docker daemon, no root required |
| `/data` volume for bot data | `~/hub/knowledge/animaya/` | This project (v2) | Git-versioned with Hub, shared with other agents |
| Platform container manages bot lifecycle | Single-user LXC with direct systemd | This project (v2) | Simpler, no orchestration layer |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `unset CLAUDECODE` in bash clears env for child processes | Pattern 2 (run.sh) | SDK subprocess still hangs — would need alternative isolation approach |
| A2 | `loginctl enable-linger` is available on the target LXC | Pattern 3 (systemd) | Service won't start on boot — fallback: cron @reboot or root-level service |
| A3 | Claude Box LXC runs systemd (not OpenRC or runit) | Pattern 3 | Entire systemd approach invalid — would need init system detection |
| A4 | `python3 -m venv` is available on LXC without installing python3-venv separately | Standard Stack | setup.sh must `apt install python3-venv` first on Debian-based LXC |
| A5 | Node.js on Claude Box is managed separately from the system package manager | Pitfall 5 | apt install node could conflict; D-03 skip logic still sufficient |

## Open Questions

1. **Does the LXC use systemd user mode or require system-level service?**
   - What we know: D-05 says no root required; systemd user mode is the standard no-root approach
   - What's unclear: Some minimal LXC images disable user systemd instances
   - Recommendation: setup.sh should detect with `systemctl --user status` and fall back to a note instructing root-level install if user mode fails

2. **Claude Code CLI path on LXC (flagged in STATE.md)**
   - What we know: CONTEXT.md says Claude Box "should have" Node.js; INST-04 is about CLAUDECODE env var, not CLI path
   - What's unclear: Whether `claude` CLI is on PATH or requires full path for Phase 2+ invocations
   - Recommendation: Phase 1 doesn't invoke Claude CLI directly; document as a Phase 2 research item

3. **Migration handling (D-08 — Claude's discretion)**
   - Recommendation: Handle inline in setup.sh via a simple version file (`~/.animaya-version`). If installed version < current version, run migration steps. No separate script needed for v1 scale.

4. **Uninstall path (Claude's discretion)**
   - Recommendation: Defer `setup.sh --uninstall` to Phase 3 (module system). Phase 1 has no module artifacts to clean up; a manual 3-command uninstall (systemctl disable, rm dir, rm service file) is sufficient and documented in README.

## Environment Availability

| Dependency | Required By | Available (dev machine) | Notes |
|------------|------------|------------------------|-------|
| Python 3.12+ | venv + bot | 3.14.2 on dev | Target LXC needs 3.12+ — [ASSUMED] Claude Box ships with it |
| Node.js | D-03 check | 23.11.0 on dev | Claude Box has it for Claude Code; setup.sh checks, skips if present |
| systemd | Service management | Not on macOS dev | Present on LXC [ASSUMED] — standard on Debian/Ubuntu LXC |
| pip | Package install | 25.3 on dev | Bundled with Python venv |
| git | Repo clone, Hub versioning | Present | Standard on any dev box |

**Missing dependencies with no fallback:** None identified for Phase 1 scope.
**Note:** Environment checks above are for the dev machine (macOS). The target is an LXC — all assumptions about LXC environment are tagged [ASSUMED] and may need verification during execution.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `python -m pytest tests/ -x -q` |
| Full suite command | `python -m pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INST-01 | setup.sh is executable and runs without error | smoke | `bash -n scripts/setup.sh` (syntax check) | Wave 0 |
| INST-02 | Venv created, deps installed | integration | `python -m pytest tests/test_install.py::test_venv_exists -x` | Wave 0 |
| INST-03 | Systemd unit file has correct Restart= and logging directives | unit | `python -m pytest tests/test_install.py::test_service_file -x` | Wave 0 |
| INST-04 | run.sh unsets CLAUDECODE before exec | unit | `python -m pytest tests/test_install.py::test_claudecode_unset -x` | Wave 0 |

### Wave 0 Gaps
- [ ] `tests/test_install.py` — covers INST-02, INST-03, INST-04 (parse service file, check run.sh content)
- [ ] `tests/conftest.py` — shared fixtures (tmp install dir)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A — no auth in Phase 1 |
| V3 Session Management | no | N/A |
| V4 Access Control | yes (minimal) | .env file permissions: `chmod 600 .env` in setup.sh |
| V5 Input Validation | yes (minimal) | Interactive prompts in setup.sh should not write shell-injectable values |
| V6 Cryptography | no | N/A |

### Known Threat Patterns for shell installer + systemd

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| .env world-readable | Information Disclosure | `chmod 600 .env` immediately after write |
| Token echoed to terminal during prompt | Information Disclosure | Use `read -rs` (silent) for token input |
| Path injection in ExecStart | Elevation of Privilege | Use absolute paths with `%h` expansion in service file |

## Sources

### Primary (HIGH confidence)
- `bot/main.py` — existing startup sequence and env validation pattern [VERIFIED: codebase]
- `pyproject.toml` — existing dependencies, Python version, ruff/pytest config [VERIFIED: codebase]
- `.planning/phases/01-install-foundation/01-CONTEXT.md` — locked decisions [VERIFIED: codebase]

### Secondary (MEDIUM confidence)
- systemd.service(5) man page patterns — Restart=on-failure, StandardOutput=journal, %h expansion [ASSUMED — standard systemd knowledge]
- loginctl enable-linger — standard pattern for user services on boot [ASSUMED]

### Tertiary (LOW confidence)
- Claude Code SDK CLAUDECODE=1 behavior — inferred from CONTEXT.md specifics + INST-04 requirement [ASSUMED — exact behavior not verified against SDK source]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — pyproject.toml exists, all deps declared
- Architecture: HIGH — patterns derived directly from locked decisions + existing code
- Pitfalls: MEDIUM — systemd/venv pitfalls are well-known; CLAUDECODE behavior is assumed
- CLAUDECODE sanitization: MEDIUM — requirement clearly stated in INST-04; exact SDK behavior assumed

**Research date:** 2026-04-13
**Valid until:** 2026-05-13 (stable domain — shell + systemd + Python venv)
