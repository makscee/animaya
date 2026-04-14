#!/usr/bin/env bash
set -euo pipefail

echo "sample install: ${ANIMAYA_MODULE_DIR}"

if [ -n "${ANIMAYA_HUB_DIR:-}" ]; then
  touch "${ANIMAYA_HUB_DIR}/.sample-marker"
fi

exit 0
