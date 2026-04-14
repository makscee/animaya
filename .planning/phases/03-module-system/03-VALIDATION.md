---
phase: 3
slug: module-system
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-14
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio |
| **Config file** | pyproject.toml (`[tool.pytest.ini_options]`) |
| **Quick run command** | `python -m pytest tests/modules/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/modules/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-00-01 | 00 | 0 | infra | — | pydantic v2 importable | smoke | `python -c "import pydantic; assert pydantic.VERSION.startswith('2.')"` | ❌ W0 | ⬜ pending |
| 03-01-01 | 01 | 1 | MODS-01 | — | manifest.json parses via pydantic | unit | `python -m pytest tests/modules/test_manifest.py -x` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | MODS-01 | — | invalid manifest rejected w/ clear error | unit | `python -m pytest tests/modules/test_manifest.py::test_invalid_rejected -x` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 2 | MODS-02 | — | registry JSON read/write round-trip | unit | `python -m pytest tests/modules/test_registry.py -x` | ❌ W0 | ⬜ pending |
| 03-03-01 | 03 | 2 | MODS-03 | — | install.sh executes; files created | integration | `python -m pytest tests/modules/test_lifecycle.py::test_install -x` | ❌ W0 | ⬜ pending |
| 03-03-02 | 03 | 2 | MODS-03 | — | uninstall removes all owned_paths | integration | `python -m pytest tests/modules/test_lifecycle.py::test_uninstall_cleanup -x` | ❌ W0 | ⬜ pending |
| 03-04-01 | 04 | 3 | MODS-04 | — | assembler merges core + module prompts | unit | `python -m pytest tests/modules/test_assembler.py -x` | ❌ W0 | ⬜ pending |
| 03-05-01 | 05 | 3 | MODS-05 | — | install→uninstall leaves no stale files | e2e | `python -m pytest tests/modules/test_roundtrip.py -x` | ❌ W0 | ⬜ pending |
| 03-06-01 | 06 | 3 | MODS-06 | — | no cross-module imports (AST scan) | lint | `python -m pytest tests/modules/test_isolation.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Add `pydantic>=2.0` to `pyproject.toml` dependencies
- [ ] `tests/modules/__init__.py` — package marker
- [ ] `tests/modules/conftest.py` — shared fixtures (temp Hub dir, sample manifest factory, isolated registry path)
- [ ] `tests/modules/fixtures/valid-module/` — minimal valid module (manifest.json + install.sh + uninstall.sh + prompt.md)
- [ ] `tests/modules/fixtures/invalid-manifest/` — intentionally malformed manifest
- [ ] Stubs for: `test_manifest.py`, `test_registry.py`, `test_lifecycle.py`, `test_assembler.py`, `test_roundtrip.py`, `test_isolation.py`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Bridge module dogfood install on live Hub | MODS-03 | Confirms real-world lifecycle against production-like Hub layout | Run `animaya module install bridge`, verify `registry.json` entry; run `animaya module uninstall bridge`, verify clean state |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
