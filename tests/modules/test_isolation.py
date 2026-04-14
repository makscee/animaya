"""Module isolation test (Phase 3, MODS-06).

D-20 declares MODS-06 convention-enforced, with no ruff rule and no scanner.
This test implements a minimal AST-based check that catches the common
failure mode (``from modules.other import ...``) without maintaining a
custom lint plugin. It is not exhaustive - a module could still read
another's files at runtime via importlib - but it covers the 99% case.

Run: ``python -m pytest tests/modules/test_isolation.py -v``
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MODULES_ROOT = REPO_ROOT / "modules"


def _module_dirs() -> list[Path]:
    """All first-level subdirs of modules/ that look like modules."""
    if not MODULES_ROOT.is_dir():
        return []
    return [
        p for p in sorted(MODULES_ROOT.iterdir())
        if p.is_dir() and (p / "manifest.json").is_file()
    ]


def _python_files_in(module_dir: Path) -> list[Path]:
    """Recursively list .py files under a module directory."""
    return sorted(module_dir.rglob("*.py"))


def _sibling_module_names(current: Path) -> set[str]:
    """Names of all modules EXCEPT the current one."""
    return {p.name for p in _module_dirs() if p != current}


def _is_sibling_import(imported_name: str, siblings: set[str]) -> bool:
    """True if `imported_name` (dotted) targets a sibling module."""
    if not imported_name:
        return False
    head = imported_name.split(".", 1)[0]
    # modules.<sibling> or <sibling>.<rest>  - both are forbidden
    if head == "modules":
        rest = imported_name.split(".", 2)
        return len(rest) >= 2 and rest[1] in siblings
    return head in siblings


class TestIsolation:
    """Enforce MODS-06: no cross-module code imports."""

    def test_modules_dir_discoverable(self) -> None:
        assert MODULES_ROOT.is_dir(), f"modules/ not found at {MODULES_ROOT}"
        dirs = _module_dirs()
        assert len(dirs) >= 1, "expected at least one first-party module (bridge)"

    def test_no_cross_module_absolute_imports(self) -> None:
        violations: list[str] = []
        for module_dir in _module_dirs():
            siblings = _sibling_module_names(module_dir)
            for py in _python_files_in(module_dir):
                tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
                for node in ast.walk(tree):
                    names: list[str] = []
                    if isinstance(node, ast.Import):
                        names.extend(alias.name for alias in node.names)
                    elif isinstance(node, ast.ImportFrom) and node.module is not None:
                        # level=0 means absolute import
                        if node.level == 0:
                            names.append(node.module)
                    for n in names:
                        if _is_sibling_import(n, siblings):
                            violations.append(f"{py}: imports sibling module {n!r}")
        assert not violations, "MODS-06 violations: " + "; ".join(violations)

    def test_no_cross_module_relative_imports(self) -> None:
        """Relative imports with level>0 that escape the current module dir."""
        violations: list[str] = []
        for module_dir in _module_dirs():
            for py in _python_files_in(module_dir):
                tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom) and node.level > 0:
                        # Any relative import in a module is suspicious - modules
                        # should import stdlib or ``bot.*``, not do relative imports
                        # that could target siblings.
                        violations.append(
                            f"{py}: relative import level={node.level} "
                            f"from {node.module!r} - use absolute ``bot.*`` imports instead"
                        )
        assert not violations, "MODS-06 violations: " + "; ".join(violations)

    def test_scan_covers_any_python_added_later(self) -> None:
        """Guard: if a module adds .py files, the scanner MUST find them."""
        # Find any .py anywhere under modules/ via rglob (ground-truth)
        if not MODULES_ROOT.is_dir():
            pytest.skip("modules/ missing")
        all_py = list(MODULES_ROOT.rglob("*.py"))
        # Sum via module-scoped discovery (what the other tests use)
        discovered = [p for d in _module_dirs() for p in _python_files_in(d)]
        # Every .py found by rglob from MODULES_ROOT must appear via per-module discovery
        # (sanity: the discovery logic is not missing a directory)
        assert set(discovered) == set(all_py), (
            f"scan gap: rglob found {sorted(all_py)} but discovery found {sorted(discovered)}"
        )

    def test_bridge_has_expected_shape(self) -> None:
        """Phase 3 state: bridge ships manifest + 2 scripts + prompt, no Python."""
        bridge = MODULES_ROOT / "bridge"
        assert (bridge / "manifest.json").is_file()
        assert (bridge / "install.sh").is_file()
        assert (bridge / "uninstall.sh").is_file()
        assert (bridge / "prompt.md").is_file()
        # No Python inside bridge (bridge code lives in bot/bridge/)
        assert list(bridge.rglob("*.py")) == []
