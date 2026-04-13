"""Pytest fixtures for install artifact tests."""
import pytest
from pathlib import Path


@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def setup_sh(project_root: Path) -> str:
    """Return setup.sh content."""
    return (project_root / "scripts" / "setup.sh").read_text()


@pytest.fixture
def run_sh(project_root: Path) -> str:
    """Return run.sh content."""
    return (project_root / "run.sh").read_text()


@pytest.fixture
def service_file(project_root: Path) -> str:
    """Return animaya.service content."""
    return (project_root / "systemd" / "animaya.service").read_text()
