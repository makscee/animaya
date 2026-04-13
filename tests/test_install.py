"""Tests for install artifacts: setup.sh, run.sh, systemd/animaya.service."""
import re
import subprocess
from pathlib import Path

import pytest


class TestSetupSh:
    """Tests for scripts/setup.sh install script."""

    def test_setup_sh_syntax(self, project_root: Path) -> None:
        """setup.sh passes bash syntax check."""
        path = project_root / "scripts" / "setup.sh"
        result = subprocess.run(["bash", "-n", str(path)], capture_output=True)
        assert result.returncode == 0, f"bash -n failed: {result.stderr.decode()}"

    def test_setup_sh_env_validation(self, setup_sh: str) -> None:
        """setup.sh validates TELEGRAM_BOT_TOKEN and CLAUDE_CODE_OAUTH_TOKEN."""
        assert "TELEGRAM_BOT_TOKEN" in setup_sh
        assert "CLAUDE_CODE_OAUTH_TOKEN" in setup_sh

    def test_setup_sh_venv_creation(self, setup_sh: str) -> None:
        """setup.sh creates venv with existence guard."""
        assert "python3 -m venv" in setup_sh
        # Must have an existence guard: [[ -d or similar
        assert re.search(r'\[\[.*-d.*\]\]', setup_sh) is not None

    def test_setup_sh_pip_install(self, setup_sh: str) -> None:
        """setup.sh installs deps with venv-scoped pip."""
        assert 'pip" install' in setup_sh or '"$VENV/bin/pip"' in setup_sh or "$VENV/bin/pip" in setup_sh

    def test_setup_sh_node_check(self, setup_sh: str) -> None:
        """setup.sh checks for Node.js via command -v node."""
        assert "command -v node" in setup_sh

    def test_setup_sh_env_permissions(self, setup_sh: str) -> None:
        """setup.sh protects .env with chmod 600."""
        assert "chmod 600" in setup_sh

    def test_setup_sh_no_sudo(self, setup_sh: str) -> None:
        """setup.sh does not use sudo systemctl (user mode only)."""
        assert "sudo systemctl" not in setup_sh

    def test_setup_sh_idempotent_guards(self, setup_sh: str) -> None:
        """setup.sh contains existence checks for idempotency."""
        assert re.search(r'\[\[.*-[df]', setup_sh) is not None

    def test_setup_sh_hub_dir(self, setup_sh: str) -> None:
        """setup.sh creates hub/knowledge/animaya data directory."""
        assert "hub/knowledge/animaya" in setup_sh

    def test_setup_sh_linger(self, setup_sh: str) -> None:
        """setup.sh enables linger for user-scoped systemd."""
        assert "loginctl enable-linger" in setup_sh

    def test_setup_sh_user_systemctl(self, setup_sh: str) -> None:
        """setup.sh uses systemctl --user (not root systemctl)."""
        assert "systemctl --user" in setup_sh

    def test_setup_sh_shebang(self, setup_sh: str) -> None:
        """setup.sh has correct bash shebang."""
        assert setup_sh.startswith("#!/usr/bin/env bash")

    def test_setup_sh_set_options(self, setup_sh: str) -> None:
        """setup.sh uses set -euo pipefail for safety."""
        assert "set -euo pipefail" in setup_sh


class TestRunSh:
    """Tests for run.sh systemd wrapper script."""

    def test_run_sh_syntax(self, project_root: Path) -> None:
        """run.sh passes bash syntax check."""
        path = project_root / "run.sh"
        result = subprocess.run(["bash", "-n", str(path)], capture_output=True)
        assert result.returncode == 0, f"bash -n failed: {result.stderr.decode()}"

    def test_run_sh_unsets_claudecode(self, run_sh: str) -> None:
        """run.sh unsets CLAUDECODE to prevent SDK subprocess hangs."""
        assert "unset CLAUDECODE" in run_sh

    def test_run_sh_unsets_execution_id(self, run_sh: str) -> None:
        """run.sh unsets CLAUDECODE_EXECUTION_ID."""
        assert "unset CLAUDECODE_EXECUTION_ID" in run_sh

    def test_run_sh_sources_env(self, run_sh: str) -> None:
        """run.sh sources .env to load secrets."""
        assert re.search(r'source.*\.env', run_sh) is not None

    def test_run_sh_exec_bot(self, run_sh: str) -> None:
        """run.sh exec-replaces process with python -m bot."""
        assert re.search(r'exec.*python.*-m bot', run_sh) is not None

    def test_run_sh_shebang(self, run_sh: str) -> None:
        """run.sh has correct bash shebang."""
        assert run_sh.startswith("#!/usr/bin/env bash")


class TestServiceFile:
    """Tests for systemd/animaya.service unit file."""

    def test_service_restart(self, service_file: str) -> None:
        """Service restarts automatically on failure."""
        assert "Restart=on-failure" in service_file

    def test_service_journal(self, service_file: str) -> None:
        """Service logs to systemd journal."""
        assert "StandardOutput=journal" in service_file

    def test_service_wanted_by(self, service_file: str) -> None:
        """Service is enabled for default user target."""
        assert "WantedBy=default.target" in service_file

    def test_service_exec_start(self, service_file: str) -> None:
        """Service ExecStart references run.sh."""
        assert re.search(r'ExecStart.*run\.sh', service_file) is not None

    def test_service_has_unit_section(self, service_file: str) -> None:
        """Service file has [Unit] section."""
        assert "[Unit]" in service_file

    def test_service_has_service_section(self, service_file: str) -> None:
        """Service file has [Service] section."""
        assert "[Service]" in service_file

    def test_service_has_install_section(self, service_file: str) -> None:
        """Service file has [Install] section."""
        assert "[Install]" in service_file

    def test_service_restart_sec(self, service_file: str) -> None:
        """Service has RestartSec for backoff."""
        assert "RestartSec=" in service_file
