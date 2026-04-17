---
phase: 08-bridge-extraction-supervisor-cutover
slug: bridge-extraction-supervisor-cutover
status: SECURED
threats_open: 0
threats_total: 11
asvs_level: 1
created: 2026-04-16
---

# Security Audit — Phase 8: Bridge Extraction & Supervisor Cutover

## Threat Verification

| Threat ID | Category | Disposition | Status | Evidence |
|-----------|----------|-------------|--------|----------|
| T-08-01 | I (Info Disclosure) | mitigate | CLOSED | `bot/main.py:95-100` — `logger.warning` logs only `config_path` (a Path object); `env_token` is never interpolated into any log format string. Comment on line 95 explicitly names T-08-01. |
| T-08-02 | T/E (Tampering/Elevation) | mitigate | CLOSED | `bot/modules/manifest.py:20,82-93` — `_RUNTIME_ENTRY_PATTERN = re.compile(r"^bot\.[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")` enforced by `@field_validator("runtime_entry")` on `ModuleManifest`. Rejects `os.system`, `subprocess`, and any non-`bot.*` path. |
| T-08-03 | D (DoS) | mitigate | CLOSED | `bot/modules/supervisor.py:81-83` — `start_all` wraps each module's `on_start` in `try/except Exception`; logs via `logger.exception`, emits `module.errored` event, and continues iteration. Other modules are unaffected. |
| T-08-04 | D (DoS) | mitigate | CLOSED | (a) `bot/modules/lifecycle.py:350-363` — `uninstall()` calls `on_stop` before running `uninstall.sh`. (b) `bot/modules_runtime/telegram_bridge.py:55-66` — `on_stop` calls `updater.stop()` → `stop()` → `shutdown()` in documented PTB order, each in its own try/except. (c) `bot/main.py:195-197` — shutdown order: `supervisor.stop_all()` awaited before `server.should_exit = True`. |
| T-08-05 | T (Tampering) | mitigate | CLOSED | `bot/modules/registry.py:62-69` — `write_registry` uses sibling `.tmp` file + `os.replace()` (atomic rename). `migrate_bridge_rename` at line 163 calls `write_registry`. Idempotent: returns `False` if entry not named `"bridge"`. |
| T-08-06 | I (Info Disclosure) | accept | CLOSED | `bot/modules/context.py:10` — `EventBus = Callable[[str, str, str], None]` signature is `(level, source, message)`. No config/secret values cross this interface by design. Acceptance rationale is sound: internal API, module authors control the message string. |
| T-08-07 | T (Tampering) | accept | CLOSED | Registry lives under `~/hub/knowledge/animaya/` — same process trust boundary. No new attack surface introduced in Phase 8. Acceptance rationale is sound for ASVS Level 1. |
| T-08-08 | R (Repudiation) | mitigate | CLOSED | `bot/modules/lifecycle.py:359-360` — `on_stop` failure caught with `logger.exception(...)` (full traceback), then `finally` block clears handles regardless. Uninstall continues. |
| T-08-09 | D (DoS) | mitigate | CLOSED | `bot/main.py:161` — `uvicorn_task = asyncio.create_task(server.serve(), name="uvicorn")` (task created and running) before `await supervisor.start_all(ctx)` at line 188. Dashboard is reachable even if `start_all` hangs. |
| T-08-10 | T (Tampering) | mitigate | CLOSED | `bot/main.py:92-94` — `tmp = config_path.with_suffix(".json.tmp")` then `tmp.replace(config_path)`. Matches the atomic pattern declared in the mitigation plan. |
| T-08-11 | R (Repudiation) | mitigate | CLOSED | `bot/modules/registry.py:169-171` — `logger.warning("Migrated module 'bridge' -> 'telegram-bridge' (registry + on-disk)")` emitted on every migration run. Only fires when migration actually occurs (guarded by `if migrated:`). |

## Accepted Risks Log

| Threat ID | Rationale | Scope | Phase Review |
|-----------|-----------|-------|--------------|
| T-08-06 | `AppContext.event_bus` is an internal callable. Its `(level, source, message)` signature does not carry config values. Module authors are responsible for message content; no automated enforcement needed at ASVS L1. | Internal API — bot process only | Phase 9 may add lint rule if modules grow. |
| T-08-07 | Registry file is under `~/hub/knowledge/animaya/` — same filesystem trust boundary as the bot process itself. Phase 8 reads the registry with no new network-exposed path. V1.0 already treats the filesystem as trusted. | Filesystem — same process UID | No new surface introduced. |

## Unregistered Flags

None. The `## Threat Flags` section in all three SUMMARY files (`08-01-SUMMARY.md`, `08-02-SUMMARY.md`, `08-03-SUMMARY.md`) reports no unregistered threat flags. The 08-02-SUMMARY.md explicitly states "Threat Flags: None — no new network endpoints, auth paths, or schema changes beyond what the plan's threat model covers."

## Notes

- T-08-01 mitigation deviates slightly from the plan's suggested location (`bot/main.py` inline helper) but is equivalently implemented: the seed function `_seed_telegram_bridge_token` in `bot/main.py` at lines 55-100 logs only the `config_path` Path variable. A parallel implementation `seed_bridge_token_from_env` in `bot/modules/lifecycle.py:269-305` also logs only a warning string with no token value. Both paths are safe.
- T-08-04 has three sub-components across three files; all verified present.
- The `frozen=True` AppContext dataclass (T-08-06 context) is confirmed at `bot/modules/context.py:15`: `@dataclass(frozen=True)`.
