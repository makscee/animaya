"""Identity module tests (IDEN-01..04)."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from bot.modules_runtime import identity as iden_rt


class TestIdentityInstall:
    def test_install_creates_user_soul_sentinel(self, tmp_path, monkeypatch):
        """install.sh creates USER.md, SOUL.md with placeholder, and .pending-onboarding."""
        hub_animaya = tmp_path / "hub" / "knowledge" / "animaya"
        hub_animaya.mkdir(parents=True)
        module_dir = Path(__file__).parent.parent.parent / "modules" / "identity"
        env = {
            **os.environ,
            "ANIMAYA_MODULE_DIR": str(module_dir),
            "ANIMAYA_HUB_DIR": str(hub_animaya),
            "ANIMAYA_CONFIG_JSON": "{}",
        }
        subprocess.run(
            ["bash", str(module_dir / "install.sh")],
            cwd=str(module_dir),
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        ident = tmp_path / "hub" / "knowledge" / "identity"
        assert (ident / "USER.md").is_file()
        assert (ident / "SOUL.md").is_file()
        assert (ident / ".pending-onboarding").is_file()
        assert iden_rt.PLACEHOLDER_MARKER in (ident / "USER.md").read_text()


class TestIdentityOnboarding:
    def test_sentinel_present_after_install_cleared_after_qa(self, tmp_hub_with_identity):
        """Sentinel exists post-install; write_identity_files clears it and marks initialized."""
        ident = tmp_hub_with_identity / "identity"
        assert (ident / ".pending-onboarding").exists()
        assert not iden_rt.is_identity_initialized(ident)
        iden_rt.write_identity_files("I am the user.", "Be helpful.", "Mak", identity_dir=ident)
        assert not (ident / ".pending-onboarding").exists()
        assert iden_rt.is_identity_initialized(ident)


class TestIdentityReconfigure:
    def test_identity_command_reruns_onboarding(self, tmp_hub_with_identity):
        """/identity re-run overwrites USER.md and SOUL.md with new content."""
        ident = tmp_hub_with_identity / "identity"
        iden_rt.write_identity_files("First user.", "First soul.", "Alpha", identity_dir=ident)
        first_user = (ident / "USER.md").read_text()
        iden_rt.write_identity_files("Second user.", "Second soul.", "Beta", identity_dir=ident)
        second_user = (ident / "USER.md").read_text()
        assert first_user != second_user
        assert "Beta" in second_user
        assert "Second soul." in (ident / "SOUL.md").read_text()
