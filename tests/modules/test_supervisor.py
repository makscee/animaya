"""Tests for AppContext frozen dataclass and Supervisor lifecycle manager (BRDG-01).

Covers D-8.1 / D-8.2 contracts:
- AppContext is frozen (immutable)
- Supervisor.start_all iterates registry, skips None runtime_entry, imports and awaits on_start
- Supervisor.stop_all calls on_stop in reverse order and clears handles
- Exception isolation per module (failing module doesn't block others)
- Lifecycle events emitted via ctx.event_bus
"""
from __future__ import annotations

import asyncio
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.modules.context import AppContext
from bot.modules.registry import write_registry
from bot.modules.supervisor import Supervisor


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def fake_data_path(tmp_path: Path) -> Path:
    """Tmp data directory mimicking ~/hub/knowledge/animaya/."""
    hub = tmp_path / "hub" / "knowledge" / "animaya"
    hub.mkdir(parents=True, exist_ok=True)
    return hub


@pytest.fixture
def fake_event_bus() -> tuple[list[tuple], object]:
    """Returns (events_list, bus_callable). events_list grows on each call."""
    events: list[tuple] = []

    def _bus(level: str, source: str, message: str) -> None:
        events.append((level, source, message))

    return events, _bus


@pytest.fixture
def app_ctx(fake_data_path: Path, fake_event_bus: tuple) -> AppContext:
    """AppContext built from test fixtures."""
    events, bus = fake_event_bus
    return AppContext(
        data_path=fake_data_path,
        stop_event=asyncio.Event(),
        event_bus=bus,
        dashboard_app=None,
    )


def _make_fake_runtime(name: str, handle: object = None) -> types.ModuleType:
    """Register a fake runtime module under bot.test_runtime.<name> in sys.modules."""
    mod_name = f"bot.test_runtime.{name}"
    mod = types.ModuleType(mod_name)
    _handle = handle if handle is not None else MagicMock(name=f"handle_{name}")
    mod.on_start = AsyncMock(return_value=_handle)
    mod.on_stop = AsyncMock(return_value=None)
    sys.modules[mod_name] = mod
    return mod


def _write_registry_with_entries(hub_dir: Path, entries: list[dict]) -> None:
    """Write registry.json directly (bypassing lifecycle.install() to avoid scripts)."""
    write_registry(hub_dir, {"modules": entries})


# ── Test 1: AppContext is frozen ──────────────────────────────────────

class TestAppContext:
    def test_frozen_dataclass_rejects_mutation(self, app_ctx: AppContext) -> None:
        """Test 1: AppContext.data_path cannot be mutated (FrozenInstanceError)."""
        from dataclasses import FrozenInstanceError
        with pytest.raises(FrozenInstanceError):
            app_ctx.data_path = Path("/tmp/other")  # type: ignore[misc]


# ── Tests 2–5, 8: Supervisor.start_all ───────────────────────────────

class TestSupervisorStartAll:
    async def test_start_all_empty_registry_is_noop(
        self, app_ctx: AppContext
    ) -> None:
        """Test 2: Supervisor.start_all with empty registry is a no-op."""
        sup = Supervisor()
        await sup.start_all(app_ctx)
        assert sup.get_handle("anything") is None

    async def test_start_all_skips_none_runtime_entry(
        self, app_ctx: AppContext, fake_data_path: Path
    ) -> None:
        """Test 3: Supervisor.start_all skips entries where runtime_entry is None."""
        _write_registry_with_entries(fake_data_path, [
            {
                "name": "identity",
                "version": "1.0.0",
                "manifest_version": 1,
                "installed_at": "2026-01-01T00:00:00+00:00",
                "config": {},
                "depends": [],
                "module_dir": "/tmp/identity",
                "runtime_entry": None,
            }
        ])
        sup = Supervisor()
        await sup.start_all(app_ctx)
        assert sup.get_handle("identity") is None

    async def test_start_all_imports_and_awaits_on_start(
        self, app_ctx: AppContext, fake_data_path: Path
    ) -> None:
        """Test 4: Supervisor.start_all imports runtime_entry and awaits on_start."""
        mod = _make_fake_runtime("fake_mod_a")
        _write_registry_with_entries(fake_data_path, [
            {
                "name": "fake-mod-a",
                "version": "1.0.0",
                "manifest_version": 1,
                "installed_at": "2026-01-01T00:00:00+00:00",
                "config": {"key": "val"},
                "depends": [],
                "module_dir": "/tmp/fake-mod-a",
                "runtime_entry": "bot.test_runtime.fake_mod_a",
            }
        ])
        sup = Supervisor()
        await sup.start_all(app_ctx)
        mod.on_start.assert_awaited_once_with(app_ctx, {"key": "val"})
        handle = sup.get_handle("fake-mod-a")
        assert handle is not None

    async def test_start_all_continues_past_failing_module(
        self, app_ctx: AppContext, fake_data_path: Path
    ) -> None:
        """Test 5: Failing module is skipped; other modules still start."""
        # bad module raises in on_start
        bad_mod_name = "bot.test_runtime.bad_mod"
        bad_mod = types.ModuleType(bad_mod_name)
        bad_mod.on_start = AsyncMock(side_effect=RuntimeError("boom"))
        bad_mod.on_stop = AsyncMock()
        sys.modules[bad_mod_name] = bad_mod

        good_mod = _make_fake_runtime("good_mod")

        _write_registry_with_entries(fake_data_path, [
            {
                "name": "bad-mod",
                "version": "1.0.0",
                "manifest_version": 1,
                "installed_at": "2026-01-01T00:00:00+00:00",
                "config": {},
                "depends": [],
                "module_dir": "/tmp/bad-mod",
                "runtime_entry": "bot.test_runtime.bad_mod",
            },
            {
                "name": "good-mod",
                "version": "1.0.0",
                "manifest_version": 1,
                "installed_at": "2026-01-02T00:00:00+00:00",
                "config": {},
                "depends": [],
                "module_dir": "/tmp/good-mod",
                "runtime_entry": "bot.test_runtime.good_mod",
            },
        ])
        sup = Supervisor()
        await sup.start_all(app_ctx)
        # bad-mod failed → no handle; good-mod started → has handle
        assert sup.get_handle("bad-mod") is None
        assert sup.get_handle("good-mod") is not None

    def test_get_handle_returns_none_for_missing(self) -> None:
        """Test 8: Supervisor.get_handle returns None for unknown module."""
        sup = Supervisor()
        assert sup.get_handle("does-not-exist") is None


# ── Tests 6–7: Supervisor.stop_all ───────────────────────────────────

class TestSupervisorStopAll:
    async def test_stop_all_reverse_order_and_clears(
        self, app_ctx: AppContext, fake_data_path: Path
    ) -> None:
        """Test 6: Supervisor.stop_all awaits on_stop in REVERSE registration order."""
        call_order: list[str] = []

        mod_a = _make_fake_runtime("ord_a")
        mod_b = _make_fake_runtime("ord_b")

        async def stop_a(handle: object) -> None:
            call_order.append("a")

        async def stop_b(handle: object) -> None:
            call_order.append("b")

        mod_a.on_stop = stop_a
        mod_b.on_stop = stop_b

        _write_registry_with_entries(fake_data_path, [
            {
                "name": "ord-a",
                "version": "1.0.0",
                "manifest_version": 1,
                "installed_at": "2026-01-01T00:00:00+00:00",
                "config": {},
                "depends": [],
                "module_dir": "/tmp/ord-a",
                "runtime_entry": "bot.test_runtime.ord_a",
            },
            {
                "name": "ord-b",
                "version": "1.0.0",
                "manifest_version": 1,
                "installed_at": "2026-01-02T00:00:00+00:00",
                "config": {},
                "depends": [],
                "module_dir": "/tmp/ord-b",
                "runtime_entry": "bot.test_runtime.ord_b",
            },
        ])
        sup = Supervisor()
        await sup.start_all(app_ctx)
        await sup.stop_all()
        # Started: a first, b second → stopped: b first, a second
        assert call_order == ["b", "a"]
        # Handles cleared
        assert sup.get_handle("ord-a") is None
        assert sup.get_handle("ord-b") is None

    async def test_stop_all_continues_past_failing_on_stop(
        self, app_ctx: AppContext, fake_data_path: Path
    ) -> None:
        """Test 7: Supervisor.stop_all continues past failing on_stop."""
        call_order: list[str] = []

        mod_c = _make_fake_runtime("fail_stop_c")
        mod_d = _make_fake_runtime("fail_stop_d")

        async def stop_c_fail(handle: object) -> None:
            raise RuntimeError("on_stop failed")

        async def stop_d_ok(handle: object) -> None:
            call_order.append("d")

        mod_c.on_stop = stop_c_fail
        mod_d.on_stop = stop_d_ok

        _write_registry_with_entries(fake_data_path, [
            {
                "name": "fail-stop-c",
                "version": "1.0.0",
                "manifest_version": 1,
                "installed_at": "2026-01-01T00:00:00+00:00",
                "config": {},
                "depends": [],
                "module_dir": "/tmp/fail-stop-c",
                "runtime_entry": "bot.test_runtime.fail_stop_c",
            },
            {
                "name": "fail-stop-d",
                "version": "1.0.0",
                "manifest_version": 1,
                "installed_at": "2026-01-02T00:00:00+00:00",
                "config": {},
                "depends": [],
                "module_dir": "/tmp/fail-stop-d",
                "runtime_entry": "bot.test_runtime.fail_stop_d",
            },
        ])
        sup = Supervisor()
        await sup.start_all(app_ctx)
        # Should not raise even though c fails
        await sup.stop_all()
        # d was still called despite c's failure (reversed: d first, then c fails)
        assert "d" in call_order


# ── Test 9: Lifecycle events ──────────────────────────────────────────

class TestSupervisorLifecycleEvents:
    async def test_lifecycle_events_emitted(
        self, fake_data_path: Path, fake_event_bus: tuple
    ) -> None:
        """Test 9: module.starting, module.started, module.stopping, module.stopped events emitted."""
        events, bus = fake_event_bus
        ctx = AppContext(
            data_path=fake_data_path,
            stop_event=asyncio.Event(),
            event_bus=bus,
        )
        mod = _make_fake_runtime("evt_mod")
        _write_registry_with_entries(fake_data_path, [
            {
                "name": "evt-mod",
                "version": "1.0.0",
                "manifest_version": 1,
                "installed_at": "2026-01-01T00:00:00+00:00",
                "config": {},
                "depends": [],
                "module_dir": "/tmp/evt-mod",
                "runtime_entry": "bot.test_runtime.evt_mod",
            }
        ])
        sup = Supervisor()
        await sup.start_all(ctx)
        await sup.stop_all()

        messages = [msg for _, _, msg in events]
        assert any("starting" in m for m in messages), f"Expected 'starting' event, got: {messages}"
        assert any("started" in m for m in messages), f"Expected 'started' event, got: {messages}"
        assert any("stopping" in m for m in messages), f"Expected 'stopping' event, got: {messages}"
        assert any("stopped" in m for m in messages), f"Expected 'stopped' event, got: {messages}"
