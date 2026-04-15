---
phase: 08-bridge-extraction-supervisor-cutover
plan: 01
status: complete
started: 2026-04-15
completed: 2026-04-15
---

## Summary

Established supervisor foundation for module runtime lifecycle. Added `runtime_entry` field to ModuleManifest, created AppContext frozen dataclass, and built Supervisor with start_all/stop_all methods. Extended lifecycle.install() to write runtime_entry into registry.

## Key Files

### Created
- `bot/modules/context.py` — AppContext frozen dataclass (data_path, stop_event, event_bus, dashboard_app)
- `bot/modules/supervisor.py` — Supervisor class with start_all/stop_all lifecycle management
- `tests/modules/test_supervisor.py` — Supervisor unit tests
- `tests/modules/test_bridge_module.py` — Bridge module integration test scaffolds
- `tests/modules/test_supervisor_cutover.py` — Cutover integration test scaffolds
- `tests/modules/test_bridge_config_source.py` — Config source test scaffolds

### Modified
- `bot/modules/manifest.py` — Added optional runtime_entry field to ModuleManifest
- `bot/modules/lifecycle.py` — Extended install() to propagate runtime_entry

## Self-Check: PASSED

All must_have truths verified:
- ModuleManifest accepts optional runtime_entry without breaking existing manifests
- AppContext frozen dataclass exposes required fields
- Supervisor.start_all iterates registry, calls on_start for runtime_entry modules
- Supervisor.stop_all calls on_stop in reverse registration order
- lifecycle.install() writes runtime_entry into registry entry
- Wave 0 test scaffolds exist for all success criteria
