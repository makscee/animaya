"""Tests for bot.dashboard.status — systemctl probe + recent stats (Phase 5 DASH-03)."""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

import pytest


def _fake_run_factory(stdout: str, returncode: int = 0):
    def _fake(cmd, **kwargs):  # noqa: ARG001
        class _Res:
            pass

        r = _Res()
        r.stdout = stdout
        r.stderr = ""
        r.returncode = returncode
        return r

    return _fake


# ── is_running() ─────────────────────────────────────────────────────
def test_is_running_active_when_systemctl_returns_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bot.dashboard import status

    monkeypatch.setattr(status.shutil, "which", lambda _: "/usr/bin/systemctl")
    monkeypatch.setattr(status.subprocess, "run", _fake_run_factory("active\n"))
    assert status.is_running() == "active"


def test_is_running_unknown_when_systemctl_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bot.dashboard import status

    monkeypatch.setattr(status.shutil, "which", lambda _: None)
    assert status.is_running() == "unknown"


def test_is_running_unknown_on_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    from bot.dashboard import status

    monkeypatch.setattr(status.shutil, "which", lambda _: "/usr/bin/systemctl")

    def _raise(*_a, **_kw):
        raise subprocess.TimeoutExpired(cmd="systemctl", timeout=2)

    monkeypatch.setattr(status.subprocess, "run", _raise)
    assert status.is_running() == "unknown"


# ── recent_stats() ───────────────────────────────────────────────────
def test_recent_stats_counts_installed_modules(
    temp_hub_dir: Path,
    events_log: Path,  # noqa: ARG001
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bot.dashboard import status
    from bot.modules import add_entry

    monkeypatch.setattr(status.shutil, "which", lambda _: None)

    for name in ("alpha", "beta"):
        add_entry(
            temp_hub_dir,
            {
                "name": name,
                "version": "0.1.0",
                "manifest_version": 1,
                "installed_at": "2026-04-15T00:00:00+00:00",
                "config": {},
                "depends": [],
            },
        )

    stats = status.recent_stats(temp_hub_dir)
    assert stats["modules_installed"] == 2


def test_recent_stats_counts_events_today(
    temp_hub_dir: Path,
    events_log: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bot.dashboard import status
    from bot.events import emit

    monkeypatch.setattr(status.shutil, "which", lambda _: None)

    emit("info", "bridge", "fresh-1")
    emit("info", "bridge", "fresh-2")
    # Old record: directly appended with a 2-day-old ts.
    with events_log.open("a", encoding="utf-8") as fh:
        fh.write(
            json.dumps(
                {
                    "ts": "2020-01-01T00:00:00+00:00",
                    "level": "info",
                    "source": "bridge",
                    "message": "ancient",
                }
            )
            + "\n"
        )

    stats = status.recent_stats(temp_hub_dir)
    assert stats["events_today"] == 2


def test_recent_stats_labels(
    temp_hub_dir: Path,
    events_log: Path,  # noqa: ARG001
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bot.dashboard import status

    # active → Running + green
    monkeypatch.setattr(status.shutil, "which", lambda _: "/usr/bin/systemctl")
    monkeypatch.setattr(status.subprocess, "run", _fake_run_factory("active\n"))
    s = status.recent_stats(temp_hub_dir)
    assert s["status"] == "active"
    assert s["status_label"] == "Running"
    assert s["status_dot"] == "dot-green"

    # inactive → Stopped + red
    monkeypatch.setattr(status.subprocess, "run", _fake_run_factory("inactive\n", 3))
    s = status.recent_stats(temp_hub_dir)
    assert s["status_label"] == "Stopped"
    assert s["status_dot"] == "dot-red"

    # missing → Unknown + gray
    monkeypatch.setattr(status.shutil, "which", lambda _: None)
    s = status.recent_stats(temp_hub_dir)
    assert s["status"] == "unknown"
    assert s["status_label"] == "Unknown"
    assert s["status_dot"] == "dot-gray"


# keep time import used (silence linter)
_ = time
