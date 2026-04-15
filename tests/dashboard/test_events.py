"""Tests for bot.events — JSONL event log emitter, tail reader, rotator.

Contract from Plan 05-01:
    emit(level, source, message, **details) -> None
    tail(n=50) -> list[dict]
    rotate(max_lines=10_000) -> None
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest


def test_emit_appends_jsonl(events_log: Path) -> None:
    from bot.events import emit

    emit("info", "bridge", "hello")
    emit("info", "bridge", "world")
    lines = events_log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first["level"] == "info"
    assert first["source"] == "bridge"
    assert first["message"] == "hello"
    assert "ts" in first
    second = json.loads(lines[1])
    assert second["message"] == "world"


def test_emit_with_details(events_log: Path) -> None:
    from bot.events import emit

    emit("error", "modules.install", "boom", log=["x", "y"], code=7)
    record = json.loads(events_log.read_text(encoding="utf-8").splitlines()[0])
    assert record["level"] == "error"
    assert record["source"] == "modules.install"
    assert record["details"] == {"log": ["x", "y"], "code": 7}


def test_emit_rejects_unknown_level(events_log: Path) -> None:
    from bot.events import emit

    with pytest.raises(ValueError):
        emit("debug", "bridge", "nope")
    # No record should have been written.
    assert not events_log.exists() or events_log.read_text(encoding="utf-8") == ""


def test_tail_returns_last_n_parsed(events_log: Path) -> None:
    from bot.events import emit, tail

    for i in range(7):
        emit("info", "bridge", f"msg-{i}")
    result = tail(5)
    assert len(result) == 5
    assert [r["message"] for r in result] == ["msg-2", "msg-3", "msg-4", "msg-5", "msg-6"]


def test_tail_empty_returns_empty_list(events_log: Path) -> None:
    from bot.events import tail

    assert not events_log.exists()
    assert tail() == []


def test_tail_skips_corrupt_lines(events_log: Path) -> None:
    from bot.events import emit, tail

    emit("info", "bridge", "good-1")
    # Inject a corrupt line between two valid records.
    with events_log.open("a", encoding="utf-8") as fh:
        fh.write("this is not json\n")
    emit("info", "bridge", "good-2")
    result = tail()
    assert len(result) == 2
    assert [r["message"] for r in result] == ["good-1", "good-2"]


def test_rotate_truncates_to_max_lines(events_log: Path) -> None:
    from bot.events import emit, rotate

    for i in range(150):
        emit("info", "bridge", f"m{i}")
    rotate(max_lines=100)
    lines = events_log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 100
    first = json.loads(lines[0])
    last = json.loads(lines[-1])
    assert first["message"] == "m50"
    assert last["message"] == "m149"


def test_rotate_noop_when_under_cap(events_log: Path) -> None:
    from bot.events import emit, rotate

    for i in range(5):
        emit("info", "bridge", f"m{i}")
    before = events_log.read_text(encoding="utf-8")
    rotate(max_lines=100)
    after = events_log.read_text(encoding="utf-8")
    assert before == after


def test_rotate_noop_when_file_missing(events_log: Path) -> None:
    from bot.events import rotate

    assert not events_log.exists()
    # Should not raise.
    rotate(max_lines=100)
    assert not events_log.exists()


def test_emit_creates_parent_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    nested = tmp_path / "deeply" / "nested" / "events.log"
    monkeypatch.setenv("ANIMAYA_EVENTS_LOG", str(nested))
    from bot.events import emit

    emit("warn", "assembler", "deep")
    assert nested.is_file()
    record = json.loads(nested.read_text(encoding="utf-8").splitlines()[0])
    assert record["level"] == "warn"


def test_ts_is_iso_utc(events_log: Path) -> None:
    from bot.events import emit

    emit("info", "bridge", "time-check")
    record = json.loads(events_log.read_text(encoding="utf-8").splitlines()[0])
    ts = record["ts"]
    # ISO-8601, UTC — ends with +00:00 or Z.
    assert ts.endswith("+00:00") or ts.endswith("Z")
    parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None


def test_emit_handles_newlines_in_message(events_log: Path) -> None:
    """Log injection guard — newlines must be JSON-escaped (T-05-01-05)."""
    from bot.events import emit, tail

    emit("info", "bridge", "multi\nline\nmessage")
    # Raw file should contain exactly one physical line (trailing \n from emit).
    lines = events_log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    records = tail()
    assert len(records) == 1
    assert records[0]["message"] == "multi\nline\nmessage"
