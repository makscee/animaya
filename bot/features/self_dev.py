"""Self-development via bot.Dockerfile.

Bots can ONLY install packages by editing bot.Dockerfile.
Runtime pip is blocked. The platform rebuilds the container from this file.

Usage:
  python -m bot.features.self_dev dockerfile show
  python -m bot.features.self_dev dockerfile append "RUN pip install pandas==2.1.0"
  python -m bot.features.self_dev dockerfile add-package pandas
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_data_dir = Path(os.environ.get("DATA_PATH", "/data"))


def show_dockerfile() -> str:
    """Show current bot.Dockerfile contents."""
    dockerfile = _data_dir / "bot.Dockerfile"
    if not dockerfile.exists():
        return "(empty — no self-modifications yet)"
    return dockerfile.read_text(encoding="utf-8")


def append_dockerfile(line: str) -> str:
    """Append a line to bot.Dockerfile."""
    dockerfile = _data_dir / "bot.Dockerfile"
    existing = dockerfile.read_text(encoding="utf-8") if dockerfile.exists() else ""
    if line.strip() in existing:
        return f"Already in bot.Dockerfile: {line}"
    with open(dockerfile, "a", encoding="utf-8") as f:
        f.write(line.rstrip() + "\n")
    return f"Added to bot.Dockerfile: {line}\nRequest a container rebuild for changes to take effect."


def add_package(package: str) -> str:
    """Add a pip install line to bot.Dockerfile for a package."""
    line = f"RUN _pip_blocked install --no-cache-dir {package}"
    return append_dockerfile(line)


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m bot.features.self_dev <command> [args]")
        print("Commands:")
        print("  dockerfile show")
        print("  dockerfile append <line>")
        print("  dockerfile add-package <pkg>")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "dockerfile":
        if len(sys.argv) >= 3 and sys.argv[2] == "show":
            print(show_dockerfile())
        elif len(sys.argv) >= 4 and sys.argv[2] == "append":
            print(append_dockerfile(" ".join(sys.argv[3:])))
        elif len(sys.argv) >= 4 and sys.argv[2] == "add-package":
            print(add_package(sys.argv[3]))
        else:
            print("Usage: dockerfile show | append <line> | add-package <pkg>")
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
