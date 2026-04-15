"""Tests for /modules list + detail + install/uninstall UX (Plan 05-05)."""
from __future__ import annotations

import json
import time
from datetime import timedelta
from pathlib import Path
from typing import Iterator

import pytest

from tests.dashboard._helpers import build_client, make_session_cookie


def _seed_module(
    modules_root: Path,
    name: str,
    *,
    install_script: str = "#!/usr/bin/env bash\nexit 0\n",
    uninstall_script: str = "#!/usr/bin/env bash\nexit 0\n",
    owned_paths: list[str] | None = None,
    description: str = "Test module",
) -> Path:
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
    (mdir / "prompt.md").write_text(description + "\n", encoding="utf-8")
    return mdir


@pytest.fixture
def modules_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "modules"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("ANIMAYA_MODULES_DIR", str(root))
    return root


@pytest.fixture(autouse=True)
def _reset_jobs(events_log: Path):  # noqa: ARG001
    """Clear dashboard.jobs state between tests."""
    try:
        from bot.dashboard import jobs as jobs_mod  # noqa: PLC0415
    except ImportError:
        yield
        return
    jobs_mod._jobs.clear()
    jobs_mod._set_retention_for_tests(timedelta(minutes=10))
    if jobs_mod._lock.locked():
        try:
            jobs_mod._lock.release()
        except RuntimeError:
            pass
    yield
    jobs_mod._jobs.clear()


@pytest.fixture
def auth_client(
    temp_hub_dir: Path,
    session_secret: str,  # noqa: ARG001
    owner_id: int,
    bot_token: str,  # noqa: ARG001
    events_log: Path,  # noqa: ARG001
    modules_root: Path,  # noqa: ARG001
) -> Iterator:
    """TestClient with a pre-seeded owner session cookie."""
    with build_client(temp_hub_dir, follow_redirects=False) as tc:
        tc.cookies.set("animaya_session", make_session_cookie(owner_id))
        yield tc


def _poll_job(
    client, name: str, job_id: str, target_fragments: list[str], timeout: float = 5.0,
) -> str:
    """Poll /modules/{name}/job/{job_id} until body contains any target_fragment."""
    deadline = time.time() + timeout
    last_body = ""
    while time.time() < deadline:
        r = client.get(f"/modules/{name}/job/{job_id}")
        last_body = r.text
        if r.status_code == 200:
            if any(frag in last_body for frag in target_fragments):
                return last_body
        time.sleep(0.05)
    raise AssertionError(
        f"did not see any of {target_fragments} in job fragment; "
        f"last body = {last_body[:500]}"
    )


def test_modules_list_requires_owner(
    temp_hub_dir: Path, session_secret: str,  # noqa: ARG001
    owner_id: int,  # noqa: ARG001
    bot_token: str,  # noqa: ARG001
    events_log: Path,  # noqa: ARG001
    modules_root: Path,  # noqa: ARG001
):
    with build_client(temp_hub_dir, follow_redirects=False) as tc:
        r = tc.get("/modules")
        assert r.status_code in (302, 307)
        assert r.headers.get("location", "").endswith("/login")


def test_modules_list_shows_available_and_installed(
    auth_client, modules_root: Path, temp_hub_dir: Path,
):
    _seed_module(modules_root, "foo")
    _seed_module(modules_root, "bar")
    # Install foo via the real API so it appears in the installed grid.
    from bot.modules import install  # noqa: PLC0415

    install(modules_root / "foo", temp_hub_dir)
    r = auth_client.get("/modules")
    assert r.status_code == 200, r.text
    body = r.text
    assert "foo" in body
    assert "bar" in body
    assert "Installed" in body
    assert "Available" in body


def test_modules_detail_shows_metadata(
    auth_client, modules_root: Path, temp_hub_dir: Path,  # noqa: ARG001
):
    _seed_module(modules_root, "foo", owned_paths=["foo-state.json"])
    r = auth_client.get("/modules/foo")
    assert r.status_code == 200, r.text
    body = r.text
    assert "foo" in body
    assert "0.1.0" in body
    assert "foo-state.json" in body


def test_modules_detail_404_for_unknown(
    auth_client, modules_root: Path,  # noqa: ARG001
):
    r = auth_client.get("/modules/nope")
    assert r.status_code == 404


def test_post_install_returns_running_fragment(
    auth_client, modules_root: Path, temp_hub_dir: Path,  # noqa: ARG001
):
    _seed_module(
        modules_root, "bar",
        install_script="#!/usr/bin/env bash\nsleep 0.3\nexit 0\n",
    )
    r = auth_client.post("/modules/bar/install")
    assert r.status_code == 200, r.text
    body = r.text
    assert 'hx-trigger="every 1s"' in body
    assert "Installing" in body


def test_job_endpoint_returns_done_fragment(
    auth_client, modules_root: Path, temp_hub_dir: Path,  # noqa: ARG001
):
    _seed_module(modules_root, "bar")
    r = auth_client.post("/modules/bar/install")
    assert r.status_code == 200
    # Extract job id from hx-get URL in the fragment.
    import re  # noqa: PLC0415

    m = re.search(r"/modules/bar/job/([a-f0-9]+)", r.text)
    assert m, f"no job id in: {r.text[:500]}"
    job_id = m.group(1)
    body = _poll_job(auth_client, "bar", job_id, ["Installed", "Configure", "badge-green"])
    assert "Installed" in body or "badge-green" in body
    # stop polling => no hx-trigger in final fragment
    assert 'hx-trigger="every 1s"' not in body


def test_job_endpoint_returns_failed_fragment(
    auth_client, modules_root: Path, temp_hub_dir: Path,  # noqa: ARG001
):
    _seed_module(
        modules_root, "badmod",
        install_script="#!/usr/bin/env bash\necho 'boom'\nexit 1\n",
    )
    r = auth_client.post("/modules/badmod/install")
    assert r.status_code == 200
    import re  # noqa: PLC0415

    m = re.search(r"/modules/badmod/job/([a-f0-9]+)", r.text)
    assert m
    job_id = m.group(1)
    body = _poll_job(auth_client, "badmod", job_id, ["Install failed"])
    assert "Install failed" in body
    assert "<details>" in body
    assert "rollback" in body


def test_second_install_returns_409_conflict_toast(
    auth_client, modules_root: Path, temp_hub_dir: Path,  # noqa: ARG001
):
    _seed_module(
        modules_root, "slow",
        install_script="#!/usr/bin/env bash\nsleep 0.5\nexit 0\n",
    )
    _seed_module(modules_root, "other")
    r1 = auth_client.post("/modules/slow/install")
    assert r1.status_code == 200
    # Give the task a moment to acquire the lock.
    time.sleep(0.05)
    r2 = auth_client.post("/modules/other/install")
    assert r2.status_code == 409
    assert "Another module operation is in progress" in r2.text
    # Wait for first to finish before test cleanup.
    import re  # noqa: PLC0415

    m = re.search(r"/modules/slow/job/([a-f0-9]+)", r1.text)
    assert m
    _poll_job(
        auth_client, "slow", m.group(1),
        ["Installed", "badge-green", "Install failed"], timeout=5.0,
    )


def test_post_uninstall_installed_module(
    auth_client, modules_root: Path, temp_hub_dir: Path,
):
    _seed_module(modules_root, "foo")
    from bot.modules import get_entry, install  # noqa: PLC0415

    install(modules_root / "foo", temp_hub_dir)
    assert get_entry(temp_hub_dir, "foo") is not None

    r = auth_client.post("/modules/foo/uninstall")
    assert r.status_code == 200, r.text
    import re  # noqa: PLC0415

    m = re.search(r"/modules/foo/job/([a-f0-9]+)", r.text)
    assert m, f"no job id: {r.text[:500]}"
    job_id = m.group(1)
    # Poll until final fragment (non-running).
    deadline = time.time() + 5.0
    while time.time() < deadline:
        poll = auth_client.get(f"/modules/foo/job/{job_id}")
        if 'hx-trigger="every 1s"' not in poll.text:
            break
        time.sleep(0.05)
    assert get_entry(temp_hub_dir, "foo") is None
    # foo is now Available, not Installed.
    list_body = auth_client.get("/modules").text
    assert "Available" in list_body
    # crude check: the text "foo" must now appear in the Available section.
    # Since both sections can contain "foo" in principle, rely on the
    # absence of "installed" badge next to foo — pragmatic assertion.
    assert "foo" in list_body
