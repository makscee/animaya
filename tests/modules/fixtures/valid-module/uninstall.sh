#!/usr/bin/env bash
set -euo pipefail

echo "sample uninstall"

if [ -n "${ANIMAYA_HUB_DIR:-}" ]; then
  rm -f "${ANIMAYA_HUB_DIR}/.sample-marker"
fi

exit 0
