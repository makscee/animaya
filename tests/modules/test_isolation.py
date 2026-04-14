"""Tests for cross-module import isolation (Phase 3, MODS-06).

Modules must not import each other. Enforced via AST walk over Python
files under modules/*/ and registry entries.
"""
from __future__ import annotations

import ast
from pathlib import Path

import importlib.util

import pytest

_HAS_MODS = importlib.util.find_spec("bot.modules") is not None
pytestmark = pytest.mark.skipif(
    not _HAS_MODS, reason="bot.modules package not yet implemented"
)

if _HAS_MODS:
    import bot.modules as mods  # noqa: E402
else:
    mods = None  # type: ignore[assignment]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MODULES_ROOT = _REPO_ROOT / "modules"


def _imports_in_file(path: Path) -> list[str]:
    """Return list of imported module names from a Python file."""
    tree = ast.parse(path.read_text())
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.append(node.module)
    return names


class TestIsolation:
    def test_no_cross_module_imports(self) -> None:
        if not _MODULES_ROOT.exists():
            pytest.skip("modules/ tree not present yet")
        module_dirs = [p for p in _MODULES_ROOT.iterdir() if p.is_dir()]
        if not module_dirs:
            pytest.skip("no installed modules to check")
        sibling_names = {p.name for p in module_dirs}
        for mod_dir in module_dirs:
            for py_file in mod_dir.rglob("*.py"):
                for imported in _imports_in_file(py_file):
                    assert not imported.startswith("modules."), (
                        f"{py_file} imports '{imported}' (cross-module import forbidden)"
                    )
                    root = imported.split(".")[0]
                    assert root not in (sibling_names - {mod_dir.name}), (
                        f"{py_file} imports sibling module '{imported}'"
                    )

    def test_no_imports_between_modules_registered_in_registry(
        self, tmp_hub_dir: Path
    ) -> None:
        registry = mods.read_registry(tmp_hub_dir)
        names = {entry["name"] for entry in registry.get("modules", [])}
        if not _MODULES_ROOT.exists() or not names:
            pytest.skip("no registered modules to check")
        for name in names:
            mod_dir = _MODULES_ROOT / name
            if not mod_dir.exists():
                continue
            for py_file in mod_dir.rglob("*.py"):
                for imported in _imports_in_file(py_file):
                    root = imported.split(".")[0]
                    assert root not in (names - {name}), (
                        f"{py_file} imports registered sibling '{imported}'"
                    )
