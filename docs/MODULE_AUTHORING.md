# Animaya Module Authoring Guide

This guide describes how to author a module for Animaya v2's module system
(Phase 3, requirements MODS-01..MODS-06). Read it before creating a new
module. The first-party `modules/bridge/` module is a minimal reference;
cite it as you build.

## Module layout

Every module is a directory under `~/animaya/modules/<name>/` containing:

```
modules/<name>/
├── manifest.json     # Required — pydantic-validated metadata
├── install.sh        # Required — lifecycle install hook
├── uninstall.sh      # Required — lifecycle uninstall hook
└── prompt.md         # Required — system-prompt snippet injected into CLAUDE.md
```

The folder name MUST match `manifest.json`'s `name` field. The installer
rejects mismatches at install time (Phase 3 threat register T-03-01-05).

## manifest.json schema (pydantic strict)

Required fields:

- `manifest_version` (int, ≥1): schema version; currently `1`.
- `name` (string, regex `^[a-z][a-z0-9_-]*$`): MUST match the folder name.
- `version` (string, regex `^\d+\.\d+\.\d+.*$`): semver prefix
  (e.g., `1.0.0`, `1.2.3-beta.1`).
- `system_prompt_path` (string): relative path to the prompt file within
  the module dir (usually `prompt.md`).
- `owned_paths` (array of strings): every file or directory this module
  creates under the Hub, expressed relative to `ANIMAYA_HUB_DIR`. See
  [owned_paths rules](#owned_paths-rules-mods-05) below.

Optional fields:

- `scripts.install` (string, default `"install.sh"`)
- `scripts.uninstall` (string, default `"uninstall.sh"`)
- `depends` (array of module names, default `[]`)
- `config_schema` (JSON Schema dict, default `null`): Phase 5 dashboard
  renders this into a config form when the user installs the module.

**Strict validation:** unknown fields are REJECTED. Schema evolution
happens via `manifest_version` bump, not by accretion.

Example (bridge module):

```json
{
  "manifest_version": 1,
  "name": "bridge",
  "version": "1.0.0",
  "system_prompt_path": "prompt.md",
  "owned_paths": [],
  "scripts": {"install": "install.sh", "uninstall": "uninstall.sh"},
  "depends": [],
  "config_schema": null
}
```

## Lifecycle contract (D-11)

Both `install.sh` and `uninstall.sh` are invoked as `bash <script>` by
`bot.modules.lifecycle` with:

- Working directory: the module directory.
- Env vars injected:
  - `ANIMAYA_MODULE_DIR` — absolute path to this module's directory.
  - `ANIMAYA_HUB_DIR` — absolute path to `~/hub/knowledge/animaya/`
    (the hub state root).
  - `ANIMAYA_CONFIG_JSON` — JSON string of user-supplied config
    (may be `{}`). Parse with `jq`, `python -c`, etc.
- Exit code: `0` on success, non-zero on failure.

**Install failure triggers auto-rollback (D-13):** the installer runs
your `uninstall.sh` best-effort to clean partial state, then verifies no
`owned_paths` remain. No registry entry is written on failure.

**Reinstall is rejected (D-14):** installing an already-installed module
raises a clear `ValueError("... already installed ...")`. The user must
uninstall first.

## Idempotency requirement (CRITICAL)

`uninstall.sh` MUST be idempotent and MUST NOT fail when run on partial
or absent state. The installer may call it mid-rollback after `install.sh`
has only partially created `owned_paths`.

Good pattern (idempotent, safe on missing state):

```bash
#!/usr/bin/env bash
set -euo pipefail
rm -rf "${ANIMAYA_HUB_DIR}/my-module-data"   # rm -rf is idempotent
rm -f  "${ANIMAYA_HUB_DIR}/my-config.json"
```

Bad pattern (fails if dir missing):

```bash
#!/usr/bin/env bash
set -euo pipefail
rmdir "${ANIMAYA_HUB_DIR}/my-module-data"    # fails if dir missing
```

Every script MUST start with:

```bash
#!/usr/bin/env bash
set -euo pipefail
```

Silent failure on unset vars or mid-pipe errors corrupts rollback state.

## owned_paths rules (MODS-05)

Every file or directory your module creates under the Hub MUST be listed
in `owned_paths`. The installer runs a leakage audit after uninstall and
raises `RuntimeError` if any listed path still exists. It also rejects
malformed entries at install time.

Rules:

- RELATIVE to `ANIMAYA_HUB_DIR`. No leading `/`, no absolute paths.
- No `..` traversal segments (rejected at install time; closes
  threat T-03-01-02).
- Directories are OK — their contents are cleaned with them when you
  `rm -rf` the dir in `uninstall.sh`.
- Example: `["identity/me.md", "identity/owner.md"]`.
- Empty `owned_paths: []` is allowed when your module creates no hub
  artifacts (e.g., the bridge module: its Python code is in `bot/bridge/`,
  managed by git, not by the installer).

## Dependencies (D-15)

`depends` lists other module names that must already be installed before
this one. No auto-install cascade — the installer rejects the install
with `ValueError("missing dependency for <name>: [...]")`.

Uninstall is also blocked if another installed module `depends` on yours;
the user must uninstall dependents first.

## prompt.md — system prompt injection (D-17)

Your module's `prompt.md` content is wrapped as
`<module name="{your_name}">...</module>` in the assembled `CLAUDE.md`,
which Claude sees at every bot call. Keep prompts focused and concise —
they are injected into every Claude invocation.

The assembler escapes `</module>` inside your prompt as `&lt;/module&gt;`
to prevent one module from closing another's XML section (threat
T-03-04-01). You do not need to escape it yourself, but be aware the
literal string will render escaped if you write it.

Assembled CLAUDE.md is rebuilt at every `install()` and `uninstall()`
call and at bot startup, so your prompt edits take effect the next time
the bot initializes a Claude query.

## MODS-06 — module isolation (CONVENTION)

Modules MUST NOT import code from sibling modules. Communication happens
exclusively through shared Hub files (markdown, JSON) under
`ANIMAYA_HUB_DIR`. If you find yourself needing to reach across modules,
it means the shared state belongs in a common Hub file that both modules
read/write independently.

This is **convention-enforced** in Phase 3 (no runtime lint rule) and
validated by `tests/modules/test_isolation.py`, which AST-scans module
source trees for cross-module imports. Violations break CI and are
caught at review time.

## Anti-patterns (avoid)

- **Writing to paths not in `owned_paths`.** The leakage check will
  miss them; uninstall leaves garbage in the hub. Declare every path
  you create.
- **Absolute paths in `owned_paths`.** Rejected at install time with
  `ValueError`.
- **`..` path segments.** Rejected at install time (T-03-01-02).
- **Mutable install side-effects outside the hub.** Install must not
  modify the repo, system config, or user's `$HOME` beyond
  `${ANIMAYA_HUB_DIR}`.
- **Runtime pip / npm.** Add Python deps to `pyproject.toml`, or
  document system requirements in your prompt.md. The installer does
  NOT resolve package deps.
- **Silent failure.** Scripts must `set -euo pipefail` and exit
  non-zero on any error so the installer can roll back cleanly.
- **Storing secrets in `prompt.md`.** prompt.md lands verbatim in
  the assembled CLAUDE.md and is visible to anyone reading the hub.
  Use env vars or dashboard-supplied `config_schema` for secrets.
- **`manifest.json` with extra fields.** Strict validation rejects
  unknown keys — bump `manifest_version` to evolve.

## Testing your module

Use `modules/bridge/` as a starting template. Validate your manifest:

```bash
python -c "from bot.modules.manifest import validate_manifest; \
from pathlib import Path; \
print(validate_manifest(Path('modules/your-module')))"
```

Dry-run install against an isolated tmp hub from a Python REPL:

```python
from pathlib import Path
from bot.modules import install, uninstall

tmp_hub = Path('/tmp/animaya-dryrun')
tmp_hub.mkdir(parents=True, exist_ok=True)
module_dir = Path('modules/your-module').resolve()

entry = install(module_dir, tmp_hub, config={})
print(entry)
uninstall("your-module", tmp_hub, module_dir)
```

Run the full roundtrip test suite:

```bash
python -m pytest tests/modules/ -v
```

## Reference: the bridge module

See `modules/bridge/` for a zero-`owned_paths` module. Its `install.sh`
and `uninstall.sh` are near-no-ops because the bridge's Python code
lives in `bot/bridge/` (managed by git, not the installer). This shape
is the canonical pattern for modules whose runtime code ships with the
Animaya repo itself — the module exists solely to inject a `prompt.md`
and flip a registry entry.

Third-party modules that DO create hub artifacts will have a richer
`install.sh` (creating files, seeding dirs) matched by a richer
`uninstall.sh` (removing every path declared in `owned_paths`).
