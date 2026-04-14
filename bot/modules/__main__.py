"""Internal CLI for module lifecycle (Phase 3, D-03 / D-04).

Usage (invoked by setup.sh and integration tests — NOT a user-facing CLI):
    python -m bot.modules install <name> [--config-json '{...}']
    python -m bot.modules uninstall <name>
    python -m bot.modules list

Module directory resolves to ``<DEFAULT_MODULES_ROOT>/<name>`` and hub
directory resolves to ``DEFAULT_HUB_DIR`` (both defined in lifecycle.py).

Exit codes: 0 on success, 1 on error (matches bot/main.py convention).
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from bot.modules.lifecycle import (
    DEFAULT_HUB_DIR,
    DEFAULT_MODULES_ROOT,
    install,
    uninstall,
)
from bot.modules.registry import list_installed

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    """Entry point for ``python -m bot.modules``. Returns process exit code."""
    parser = argparse.ArgumentParser(prog="python -m bot.modules")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_install = sub.add_parser("install", help="Install a module")
    p_install.add_argument("name")
    p_install.add_argument(
        "--config-json",
        default="{}",
        help="User config as JSON string (stored in registry entry)",
    )

    p_uninstall = sub.add_parser("uninstall", help="Uninstall a module")
    p_uninstall.add_argument("name")

    sub.add_parser("list", help="List installed modules")

    args = parser.parse_args(argv)

    hub_dir: Path = DEFAULT_HUB_DIR
    modules_root: Path = DEFAULT_MODULES_ROOT

    try:
        if args.cmd == "install":
            config = json.loads(args.config_json)
            module_dir = modules_root / args.name
            entry = install(module_dir, hub_dir, config=config)
            logger.info("Installed: %s@%s", entry["name"], entry["version"])
        elif args.cmd == "uninstall":
            module_dir = modules_root / args.name
            uninstall(args.name, hub_dir, module_dir)
            logger.info("Uninstalled: %s", args.name)
        elif args.cmd == "list":
            for n in list_installed(hub_dir):
                print(n)
    except (ValueError, KeyError, RuntimeError, FileNotFoundError) as exc:
        logger.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
