"""Tests for bot.engine.modules_jobs — async install/uninstall job runner (Plan 05-05)."""
from __future__ import annotations

import asyncio
import json
from datetime import timedelta
from pathlib import Path

import pytest


def _seed_module(
    modules_root: Path,
    name: str,
    *,
    install_script: str = "#!/usr/bin/env bash\nexit 0\n",
    uninstall_script: str = "#!/usr/bin/env bash\nexit 0\n",
    owned_paths: list[str] | None = None,
) -> Path:
    """Create a minimal module directory under modules_root.

    Returns the module directory path.
    """
    mdir = modules_root / name
    mdir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "manifest_version": 1,
        "name": name,
        "version": "0.1.0",
        "system_prompt_path": "prompt.md",
        "owned_paths": list(owned_paths or []),
        "scripts": {"install": "install.sh", "uninstall": "uninstall.sh"},
        "depends": [],
        "config_schema": None,
    }
    (mdir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    install_sh = mdir / "install.sh"
    install_sh.write_text(install_script, encoding="utf-8")
    install_sh.chmod(0o755)
    uninstall_sh = mdir / "uninstall.sh"
    uninstall_sh.write_text(uninstall_script, encoding="utf-8")
    uninstall_sh.chmod(0o755)
    (mdir / "prompt.md").write_text("module prompt\n", encoding="utf-8")
    return mdir


@pytest.fixture
def modules_root(tmp_path: Path) -> Path:
    """Return the modules root directory under tmp_path."""
    root = tmp_path / "modules"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture(autouse=True)
def _reset_jobs_state(events_log: Path):  # noqa: ARG001
    """Clear _jobs dict + reset retention between tests so they don't leak state."""
    try:
        from bot.engine import modules_jobs as jobs_mod  # noqa: PLC0415
    except ImportError:
        pytest.skip("bot.engine.modules_jobs not yet implemented")
    jobs_mod._jobs.clear()
    # Reset retention to default (10 min) in case a test shortened it.
    jobs_mod._set_retention_for_tests(timedelta(minutes=10))
    # Ensure the lock is not held from a previous crashed test.
    if jobs_mod._lock.locked():
        try:
            jobs_mod._lock.release()
        except RuntimeError:
            pass
    yield
    jobs_mod._jobs.clear()


async def _wait_for_status(jobs_mod, job_id: str, target: set[str], timeout: float = 5.0):
    """Poll get_job until status is in target or timeout."""
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        j = jobs_mod.get_job(job_id)
        if j is not None and j.status in target:
            return j
        await asyncio.sleep(0.02)
    raise AssertionError(
        f"job {job_id} did not reach status {target}; "
        f"current = {getattr(jobs_mod.get_job(job_id), 'status', None)}"
    )


@pytest.mark.asyncio
async def test_start_install_returns_running_job(
    modules_root: Path, temp_hub_dir: Path, events_log: Path,  # noqa: ARG001
):
    from bot.engine import modules_jobs as jobs_mod  # noqa: PLC0415
    from bot.modules import get_entry  # noqa: PLC0415

    mdir = _seed_module(modules_root, "foo")
    job = await jobs_mod.start_install("foo", mdir, temp_hub_dir)
    assert job.status == "running"
    assert job.op == "install"
    assert job.module == "foo"
    final = await _wait_for_status(jobs_mod, job.id, {"done", "failed"})
    assert final.status == "done", f"job failed: {final.error}; log={final.log_lines}"
    assert get_entry(temp_hub_dir, "foo") is not None


@pytest.mark.asyncio
async def test_start_install_failure_captures_log_and_rollback(
    modules_root: Path, temp_hub_dir: Path, events_log: Path,  # noqa: ARG001
):
    from bot.engine import modules_jobs as jobs_mod  # noqa: PLC0415

    mdir = _seed_module(
        modules_root, "bad",
        install_script="#!/usr/bin/env bash\necho 'install output'\nexit 1\n",
        owned_paths=[],
    )
    job = await jobs_mod.start_install("bad", mdir, temp_hub_dir)
    final = await _wait_for_status(jobs_mod, job.id, {"done", "failed"})
    assert final.status == "failed"
    assert final.error
    # Some log record should have been captured via the bot.modules logger.
    assert len(final.log_lines) > 0
    # owned_paths empty => rollback is "clean"
    assert final.rollback == "clean"
    assert final.leaked_paths == []


@pytest.mark.asyncio
async def test_start_install_failure_dirty_rollback(
    modules_root: Path, temp_hub_dir: Path, events_log: Path,  # noqa: ARG001
):
    from bot.engine import modules_jobs as jobs_mod  # noqa: PLC0415

    # install.sh creates leaked.txt under hub, then exits 1.
    # uninstall.sh is a no-op so the leaked file remains.
    mdir = _seed_module(
        modules_root, "leaker",
        install_script=(
            "#!/usr/bin/env bash\n"
            "echo x > \"$ANIMAYA_HUB_DIR/leaked.txt\"\n"
            "exit 1\n"
        ),
        uninstall_script="#!/usr/bin/env bash\nexit 0\n",
        owned_paths=["leaked.txt"],
    )
    job = await jobs_mod.start_install("leaker", mdir, temp_hub_dir)
    final = await _wait_for_status(jobs_mod, job.id, {"done", "failed"})
    assert final.status == "failed"
    assert final.rollback == "dirty"
    assert "leaked.txt" in final.leaked_paths


@pytest.mark.asyncio
async def test_second_install_while_running_raises_InProgressError(
    modules_root: Path, temp_hub_dir: Path, events_log: Path,  # noqa: ARG001
):
    from bot.engine import modules_jobs as jobs_mod  # noqa: PLC0415

    slow = _seed_module(
        modules_root, "slow",
        install_script="#!/usr/bin/env bash\nsleep 0.5\nexit 0\n",
    )
    other = _seed_module(modules_root, "other")
    first = await jobs_mod.start_install("slow", slow, temp_hub_dir)
    # Give the task a moment to acquire the lock.
    await asyncio.sleep(0.05)
    with pytest.raises(jobs_mod.InProgressError):
        await jobs_mod.start_install("other", other, temp_hub_dir)
    await _wait_for_status(jobs_mod, first.id, {"done", "failed"}, timeout=5.0)


@pytest.mark.asyncio
async def test_start_uninstall_clears_entry(
    modules_root: Path, temp_hub_dir: Path, events_log: Path,  # noqa: ARG001
):
    from bot.engine import modules_jobs as jobs_mod  # noqa: PLC0415
    from bot.modules import get_entry, install  # noqa: PLC0415

    mdir = _seed_module(modules_root, "keep")
    install(mdir, temp_hub_dir)
    assert get_entry(temp_hub_dir, "keep") is not None
    job = await jobs_mod.start_uninstall("keep", temp_hub_dir, mdir)
    final = await _wait_for_status(jobs_mod, job.id, {"done", "failed"})
    assert final.status == "done", f"uninstall failed: {final.error}"
    assert get_entry(temp_hub_dir, "keep") is None


@pytest.mark.asyncio
async def test_get_job_returns_None_after_eviction(
    modules_root: Path, temp_hub_dir: Path, events_log: Path,  # noqa: ARG001
):
    from bot.engine import modules_jobs as jobs_mod  # noqa: PLC0415

    mdir = _seed_module(modules_root, "ev")
    job = await jobs_mod.start_install("ev", mdir, temp_hub_dir)
    await _wait_for_status(jobs_mod, job.id, {"done", "failed"})
    # Shorten retention AFTER the job finished so _gc evicts on next access.
    jobs_mod._set_retention_for_tests(timedelta(seconds=0))
    assert jobs_mod.get_job(job.id) is None


@pytest.mark.asyncio
async def test_install_does_not_block_event_loop(
    modules_root: Path, temp_hub_dir: Path, events_log: Path,  # noqa: ARG001
):
    from bot.engine import modules_jobs as jobs_mod  # noqa: PLC0415

    mdir = _seed_module(
        modules_root, "slower",
        install_script="#!/usr/bin/env bash\nsleep 0.3\nexit 0\n",
    )
    job = await jobs_mod.start_install("slower", mdir, temp_hub_dir)
    # If subprocess blocked the loop, this 0.1s sleep wouldn't complete
    # while the 0.3s install is running.
    start = asyncio.get_event_loop().time()
    await asyncio.sleep(0.1)
    elapsed = asyncio.get_event_loop().time() - start
    assert elapsed < 0.25  # loop remained responsive
    await _wait_for_status(jobs_mod, job.id, {"done", "failed"}, timeout=5.0)


@pytest.mark.asyncio
async def test_events_emitted_on_install_and_failure(
    modules_root: Path, temp_hub_dir: Path, events_log: Path, monkeypatch,  # noqa: ARG001
):
    from bot.engine import modules_jobs as jobs_mod  # noqa: PLC0415

    captured: list[tuple[str, str, str, dict]] = []

    def fake_emit(level: str, source: str, message: str, **details: object) -> None:
        captured.append((level, source, message, dict(details)))

    monkeypatch.setattr(jobs_mod, "events_emit", fake_emit)

    ok_dir = _seed_module(modules_root, "okm")
    job_ok = await jobs_mod.start_install("okm", ok_dir, temp_hub_dir)
    await _wait_for_status(jobs_mod, job_ok.id, {"done", "failed"})
    assert any(
        lvl == "info" and src == "modules.install" for (lvl, src, _m, _d) in captured
    ), f"captured = {captured}"

    bad_dir = _seed_module(
        modules_root, "bad2",
        install_script="#!/usr/bin/env bash\nexit 1\n",
    )
    captured.clear()
    job_bad = await jobs_mod.start_install("bad2", bad_dir, temp_hub_dir)
    await _wait_for_status(jobs_mod, job_bad.id, {"done", "failed"})
    failures = [
        (lvl, src, m, d) for (lvl, src, m, d) in captured
        if lvl == "error" and src == "modules.install"
    ]
    assert failures, f"no error emit; captured = {captured}"
    # details should include a log field
    assert any("log" in d for (_l, _s, _m, d) in failures)
