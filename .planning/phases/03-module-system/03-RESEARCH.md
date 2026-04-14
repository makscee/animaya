# Phase 3: Module System - Research

**Researched:** 2026-04-14
**Domain:** Python plugin/module lifecycle — manifest validation, install/uninstall scripts, registry, CLAUDE.md assembly
**Confidence:** HIGH (all key decisions locked in CONTEXT.md; research confirms feasibility of locked design)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Module Location & Scope**
- D-01: All modules live in `~/animaya/modules/<name>/` inside the repo. First-party and user-installed modules share the same directory. No hub-side module folder in Phase 3.
- D-02: Phase 2 Telegram bridge becomes a first-party module (`modules/bridge/`). It gets a manifest, install.sh, uninstall.sh, and prompt snippet. Uninstalling it kills the bot — acceptable; lifecycle uniformity wins.
- D-03: `setup.sh` invokes the internal install API (`python -m bot.modules install bridge`) on fresh install. Idempotent: rejects on already-installed (D-11).
- D-04: No public user-facing install CLI in Phase 3. Only the Python API (`bot.modules.install(name)`, `uninstall(name)`).
- D-05: Installation is binary: installed or uninstalled. No "disabled but kept" state.

**Registry**
- D-06: `registry.json` at `~/hub/knowledge/animaya/registry.json`. Git-versioned with Hub.
- D-07: Registry entries include: `name`, `version`, `manifest_version`, `installed_at` (ISO timestamp), `config` (snapshot of user-provided config at install time).

**Manifest Schema (pydantic)**
- D-08: Required fields: `manifest_version` (int, currently 1), `name` (str, matches folder), `version` (semver str), `system_prompt_path` (str, relative to module dir), `owned_paths` (list[str]).
- D-09: Optional fields: `scripts.install`/`scripts.uninstall` (default `install.sh`/`uninstall.sh`), `depends` (list[str] of module names), `config_schema` (JSON Schema dict).
- D-10: Validation is strict: unknown fields are rejected. Schema evolution via `manifest_version` bump.

**Lifecycle Contract**
- D-11: Install scripts receive context via env vars: `ANIMAYA_MODULE_DIR`, `ANIMAYA_HUB_DIR`, `ANIMAYA_CONFIG_JSON`. No positional args. Same contract for uninstall.sh.
- D-12: Registry update order: run install.sh → on exit 0, write registry entry.
- D-13: Install failure triggers auto-rollback: invoke uninstall.sh best-effort, verify no owned_paths remain. No registry entry written.
- D-14: Reinstalling already-installed module is rejected with clear error.
- D-15: Dependency check: missing deps reject install; uninstall of a module with dependents is rejected. No auto-cascade.

**CLAUDE.md Assembly**
- D-16: Module prompts assembled in install order (ascending `installed_at` from registry).
- D-17: Each module's prompt wrapped in `<module name="{name}">...</module>` XML tags.
- D-18: Assembly trigger: end of install/uninstall AND every bot startup.
- D-19: Output written to `~/animaya/CLAUDE.md`; `bot/templates/CLAUDE.md` prepended as base/core prompt.

**MODS-06 Isolation**
- D-20: No-cross-module-imports rule is convention-enforced only. Documented in module authoring guide. No ruff rule, no import scanner.

### Claude's Discretion
- Exact field names inside registry.json (snake_case per project conventions)
- install.sh/uninstall.sh shell style — pick `#!/usr/bin/env bash` with `set -euo pipefail`
- Where the bridge module's `owned_paths` should point (DATA_PATH root vs per-chat dirs)
- Handling of `config_schema` beyond storage in Phase 3
- How dependency ordering interacts with install-order for CLAUDE.md

### Deferred Ideas (OUT OF SCOPE)
- User-facing module CLI (`animaya module install ...`) — after Phase 5 dashboard
- Structural MODS-06 enforcement (ruff rule or import scanner)
- Three-state enable/disable (installed+disabled)
- `manifest_version` migration tooling
- Bridge module reload without full bot restart
- Module `config_schema` form rendering (Phase 5)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MODS-01 | Each module is a folder with a manifest.json validated by pydantic | Pydantic v2 `ConfigDict(extra="forbid")` + `model_config` strict mode; pydantic not yet in pyproject.toml — must be added |
| MODS-02 | Each module has install.sh and uninstall.sh lifecycle scripts | Bash `set -euo pipefail` contract; env-var injection pattern confirmed; rollback via best-effort uninstall.sh call |
| MODS-03 | Module registry (registry.json) tracks installed modules and their state | Plain JSON file at hub path; atomic write via temp-file + rename; load/save with `json` stdlib |
| MODS-04 | CLAUDE.md assembler merges core + installed module system prompts | `bot/main.py:assemble_claude_md()` stub already exists — extend it; install-order sort from `installed_at` ISO strings |
| MODS-05 | Uninstall leaves zero artifacts — enforced at manifest schema level | `owned_paths` in manifest; post-uninstall leakage check walks each declared path |
| MODS-06 | Modules communicate only through shared Hub files, no inter-module code imports | Convention-only enforcement (D-20); document in module authoring guide |
</phase_requirements>

---

## Summary

Phase 3 delivers the manifest-driven module lifecycle machinery for Animaya v2. All key design decisions are locked in CONTEXT.md from the discuss-phase session; this research validates feasibility and surfaces implementation-critical details.

The most important gap found: **pydantic is not in pyproject.toml**. FastAPI transitively brings pydantic, but it is not declared as a direct dependency. Phase 3 Wave 0 must add `"pydantic>=2.0"` as a direct dependency. Pydantic v2 `ConfigDict(extra="forbid")` directly implements the D-10 strict-manifest requirement with no custom code needed.

The existing `assemble_claude_md()` stub in `bot/main.py` already writes HTML comment markers (`<!-- module-prompts-start -->`, `<!-- module-prompts-end -->`); Phase 3 replaces the stub body while keeping the function signature — test compatibility is maintained. The test suite pattern (class-based pytest, `tmp_path` fixtures, `monkeypatch`) is well-established and directly applicable to module system tests.

**Primary recommendation:** Build `bot/modules/` as a pure Python package (manifest.py → registry.py → assembler.py → `__init__.py` public API → `__main__.py` CLI entrypoint), then add `modules/bridge/` as the first-party bridge module exercising the full lifecycle.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | >=2.0 (latest: 2.13) | Manifest schema validation with strict mode | `ConfigDict(extra="forbid")` implements D-10 with zero custom code; already used transitively by FastAPI |
| json (stdlib) | 3.12 built-in | Registry read/write | No dep overhead; registry.json is simple flat structure |
| pathlib (stdlib) | 3.12 built-in | All filesystem paths | Project convention (CLAUDE.md): `use Path for filesystem paths` |
| subprocess (stdlib) | 3.12 built-in | Running install.sh/uninstall.sh with env injection | Standard for script invocation; supports `env=` kwarg for D-11 |
| datetime (stdlib) | 3.12 built-in | ISO timestamp for `installed_at` field | `datetime.now(UTC).isoformat()` produces sortable ISO-8601 strings for D-16 sort |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| jinja2 | >=3.1.0 (already in pyproject.toml) | Template rendering | Available if assembler needs templated output; string concatenation is sufficient for current scope |
| pytest / pytest-asyncio | >=8.0 / >=0.23 (already dev deps) | Unit + integration tests | Already configured; `asyncio_mode = "auto"` active |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pydantic strict model | jsonschema + custom validator | pydantic gives typed Python objects + clear error messages for free; jsonschema is schema-only |
| JSON registry file | SQLite | SQLite is overkill for a single-user registry with <20 entries; JSON is git-diffable and human-readable |
| subprocess for scripts | Python-native install functions only | Scripts are the right boundary — they can be written by module authors in any language; pure Python entrypoints would couple module authors to the bot's Python environment |

**Installation (Wave 0 task):**
```bash
# Add to pyproject.toml dependencies array:
"pydantic>=2.0",
```

**Version verification:** [VERIFIED: WebSearch/PyPI] pydantic latest stable is 2.13 as of 2026-04-14.

---

## Architecture Patterns

### Recommended Project Structure

```
~/animaya/
├── bot/
│   └── modules/
│       ├── __init__.py          # Public API: install(), uninstall(), list_installed(), validate_manifest()
│       ├── __main__.py          # python -m bot.modules install <name>  (D-04 internal CLI)
│       ├── manifest.py          # ModuleManifest pydantic model (strict)
│       ├── registry.py          # read_registry(), write_registry(), atomic JSON I/O
│       └── assembler.py         # assemble_claude_md() — replaces bot/main.py stub
├── modules/
│   └── bridge/
│       ├── manifest.json        # First-party bridge module manifest
│       ├── install.sh           # Trivial — bridge code already in bot/bridge/
│       ├── uninstall.sh         # No-op cleanup (code stays; module just deregisters)
│       └── prompt.md            # Bridge-specific system prompt snippet
└── bot/
    └── main.py                  # Import assembler from bot.modules.assembler; remove stub
```

### Pattern 1: Pydantic Strict Manifest Model

**What:** Pydantic v2 BaseModel with `ConfigDict(extra="forbid")` rejects any unknown field at parse time, satisfying D-10.

**When to use:** Always — every manifest.json load goes through this model.

**Example:**
```python
# Source: [CITED: docs.pydantic.dev/latest/api/config/]
from pydantic import BaseModel, ConfigDict

class ModuleScripts(BaseModel):
    model_config = ConfigDict(extra="forbid")
    install: str = "install.sh"
    uninstall: str = "uninstall.sh"

class ModuleManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    manifest_version: int
    name: str
    version: str                          # semver string, validated by pattern if desired
    system_prompt_path: str               # relative to module dir
    owned_paths: list[str]                # every file/dir the module creates (MODS-05)
    scripts: ModuleScripts = ModuleScripts()
    depends: list[str] = []
    config_schema: dict | None = None     # JSON Schema passthrough; Phase 5 renders it
```

Loading:
```python
import json
from pathlib import Path

def load_manifest(module_dir: Path) -> ModuleManifest:
    raw = json.loads((module_dir / "manifest.json").read_text())
    return ModuleManifest.model_validate(raw)   # raises ValidationError on bad data
```

### Pattern 2: Registry Atomic Write

**What:** Write to a temp file then `rename()` (atomic on POSIX) to prevent partial-write corruption.

**When to use:** Every registry mutation (install, uninstall).

```python
# Source: [ASSUMED] — standard POSIX atomic-write pattern
import json, os, tempfile
from pathlib import Path

def write_registry(registry_path: Path, data: dict) -> None:
    tmp = registry_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str))
    os.replace(tmp, registry_path)   # atomic on POSIX
```

### Pattern 3: Script Invocation with Env Injection (D-11)

**What:** subprocess.run() with explicit env dict built from os.environ plus module-specific vars.

```python
import json, os, subprocess
from pathlib import Path

def run_script(script_path: Path, module_dir: Path, hub_dir: Path, config: dict) -> int:
    env = os.environ.copy()
    env["ANIMAYA_MODULE_DIR"] = str(module_dir)
    env["ANIMAYA_HUB_DIR"] = str(hub_dir)
    env["ANIMAYA_CONFIG_JSON"] = json.dumps(config)
    result = subprocess.run(
        ["bash", str(script_path)],
        env=env,
        cwd=str(module_dir),
    )
    return result.returncode
```

### Pattern 4: CLAUDE.md Assembler (replaces stub in bot/main.py)

**What:** Read registry.json, sort entries by `installed_at`, load each module's prompt file, wrap in XML tags, prepend base template.

```python
# Source: [ASSUMED] — derived from D-16, D-17, D-19 locked decisions
from pathlib import Path
import json

def assemble_claude_md(data_path: Path) -> None:
    repo_root = Path(__file__).parent.parent.parent   # ~/animaya/
    base = (repo_root / "bot" / "templates" / "CLAUDE.md").read_text()

    registry_path = data_path / "registry.json"
    entries = []
    if registry_path.exists():
        registry = json.loads(registry_path.read_text())
        entries = sorted(registry.get("modules", []), key=lambda e: e["installed_at"])

    sections = []
    for entry in entries:
        module_dir = repo_root / "modules" / entry["name"]
        manifest = load_manifest(module_dir)
        prompt_path = module_dir / manifest.system_prompt_path
        if prompt_path.exists():
            prompt = prompt_path.read_text().strip()
            sections.append(f'<module name="{entry["name"]}">\n{prompt}\n</module>')

    body = "\n\n".join(sections) if sections else "<!-- No modules installed -->"
    output = f"{base}\n\n## Installed Module Prompts\n\n{body}\n"
    (data_path / "CLAUDE.md").write_text(output)
```

### Pattern 5: Dependency Check (D-15)

```python
def check_depends(manifest: ModuleManifest, registry: dict) -> list[str]:
    """Return list of missing dependency names."""
    installed = {m["name"] for m in registry.get("modules", [])}
    return [dep for dep in manifest.depends if dep not in installed]

def check_dependents(name: str, registry: dict) -> list[str]:
    """Return list of installed modules that depend on `name`."""
    return [
        m["name"] for m in registry.get("modules", [])
        if name in m.get("manifest", {}).get("depends", [])
    ]
```

Note: D-07 says registry stores `config` snapshot but not full manifest. The dependents check above needs either manifest re-loaded from disk or `depends` stored in registry. **Planner decision:** store `depends` list in registry entry (small overhead, avoids disk read during dependency resolution).

### Anti-Patterns to Avoid

- **JSON file without atomic write:** Writing registry.json directly can produce a zero-byte file if process dies mid-write. Always use temp-file + rename.
- **subprocess.run() without explicit env:** Inheriting environment without injecting `ANIMAYA_*` vars means scripts cannot locate module/hub paths portably.
- **Assembler reading module dirs directly:** The registry is the source of truth for install order (D-16) — assembler must sort by `installed_at`, not by directory listing order.
- **pydantic v1 `class Config` syntax:** This project targets pydantic v2; use `model_config = ConfigDict(...)`, not inner `class Config`.
- **Raising ValidationError with no context:** Catch `pydantic.ValidationError` at the install entry point and log `.errors()` list for human-readable output.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Manifest field validation | Custom dict-walking validator | `pydantic.BaseModel` with `ConfigDict(extra="forbid")` | Handles type coercion, required-vs-optional, nested models, clear error messages |
| Semver string validation | Regex in manifest loader | `pydantic` field with `pattern=` or `annotated_types.Annotated` | One-liner; survives pydantic version upgrades |
| Atomic JSON write | `open().write()` directly | `os.replace(tmp, target)` pattern | POSIX rename is atomic; direct write can corrupt registry |
| ISO timestamp sorting | Custom date parser | `datetime.fromisoformat()` + sort | stdlib; ISO-8601 strings sort lexicographically anyway |

**Key insight:** The registry is a simple append/remove list — resist any temptation to add query layers or ORM. Direct JSON dict manipulation is the right tool at this scale.

---

## Common Pitfalls

### Pitfall 1: Pydantic Not in pyproject.toml

**What goes wrong:** `import pydantic` fails at runtime on a fresh venv. FastAPI transitively imports pydantic but it is not declared as a direct dependency.
**Why it happens:** pyproject.toml has `fastapi>=0.115.0` but no `pydantic` entry. Running `pip install -e .` in a fresh env without FastAPI's transitive deps will fail.
**How to avoid:** Add `"pydantic>=2.0"` to `[project].dependencies` in pyproject.toml in Wave 0.
**Warning signs:** `ModuleNotFoundError: No module named 'pydantic'` on import of `bot.modules.manifest`.

### Pitfall 2: Registry Path Doesn't Exist Yet

**What goes wrong:** First install fails with `FileNotFoundError` reading `registry.json` before it has been created.
**Why it happens:** `~/hub/knowledge/animaya/` may exist (created by bot startup) but `registry.json` is new.
**How to avoid:** `read_registry()` must return `{"modules": []}` when file does not exist. `write_registry()` must `registry_path.parent.mkdir(parents=True, exist_ok=True)` before writing.
**Warning signs:** Exception trace pointing to `registry_path.read_text()` on first-ever install.

### Pitfall 3: Rollback Runs uninstall.sh on Partial Install

**What goes wrong:** `install.sh` exits non-zero after creating some owned_paths. Rollback runs `uninstall.sh` which may itself fail if the partial state is unexpected.
**Why it happens:** D-13 specifies best-effort rollback — but uninstall.sh is module-authored and may assume a fully installed state.
**How to avoid:** Document in module authoring guide: uninstall.sh MUST be idempotent and MUST NOT fail if owned_paths are partially or fully absent. Verify with `[ -f path ] && rm path || true` patterns.
**Warning signs:** Rollback itself exits non-zero, leaving the leakage check as the only safety net.

### Pitfall 4: assemble_claude_md() Called Before Registry Exists

**What goes wrong:** Bot startup (D-18) calls assembler before any module is installed. Registry file doesn't exist.
**Why it happens:** D-18 mandates assembler runs at every startup, even on a fresh install before the bridge module is installed.
**How to avoid:** Assembler must handle missing registry gracefully (produces base-only CLAUDE.md with "<!-- No modules installed -->"). This is already the behavior of the stub — preserve it.
**Warning signs:** `FileNotFoundError` in assembler during startup before first `bot.modules install bridge` runs.

### Pitfall 5: Owned Paths Leakage Check Is Wrong Path Type

**What goes wrong:** `owned_paths` entries in manifest.json are relative paths (e.g., `"data/bridge/"`). Leakage check computes absolute path incorrectly, falsely reports clean.
**Why it happens:** `owned_paths` are relative to the module dir (or hub dir?) — the contract must be explicit.
**How to avoid:** Define in manifest schema docs that `owned_paths` are relative to `ANIMAYA_HUB_DIR`. Leakage check expands relative to hub_dir, not module_dir.
**Warning signs:** Leakage check passes but stale files remain under hub/knowledge/animaya/.

### Pitfall 6: Install Order Sort Key

**What goes wrong:** CLAUDE.md module sections appear in wrong order after reinstall sequence.
**Why it happens:** `installed_at` stored as string; if stored in non-ISO format (e.g., `"April 14, 2026"`), lexicographic sort fails.
**How to avoid:** Always store `installed_at` as `datetime.now(timezone.utc).isoformat()`. ISO-8601 is both human-readable and lexicographically sortable.
**Warning signs:** Module prompts appear in wrong order after uninstall + reinstall cycle.

---

## Code Examples

### Manifest JSON (bridge module reference)

```json
{
  "manifest_version": 1,
  "name": "bridge",
  "version": "1.0.0",
  "system_prompt_path": "prompt.md",
  "owned_paths": [],
  "scripts": {
    "install": "install.sh",
    "uninstall": "uninstall.sh"
  },
  "depends": [],
  "config_schema": null
}
```

Note: The bridge module's `owned_paths` is empty because the bridge's code lives in `bot/bridge/` (part of the repo, not a hub artifact). The bridge install.sh is a near-no-op — it validates env and logs success. The uninstall.sh does nothing except acknowledge (code removal is not in scope — the repo manages that).

### Registry JSON structure

```json
{
  "modules": [
    {
      "name": "bridge",
      "version": "1.0.0",
      "manifest_version": 1,
      "installed_at": "2026-04-14T18:35:01.221000+00:00",
      "config": {},
      "depends": []
    }
  ]
}
```

### install.sh contract (bridge example)

```bash
#!/usr/bin/env bash
set -euo pipefail

# Context injected by bot.modules installer (D-11)
echo "Installing bridge module"
echo "  Module dir: ${ANIMAYA_MODULE_DIR}"
echo "  Hub dir:    ${ANIMAYA_HUB_DIR}"
echo "  Config:     ${ANIMAYA_CONFIG_JSON}"

# Bridge has no hub artifacts to create — code lives in bot/bridge/
# Exit 0 to signal success to the installer
exit 0
```

### uninstall.sh contract (bridge example)

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "Uninstalling bridge module"
# No owned_paths to remove for bridge module
# Must be idempotent — safe to run on partial or full install
exit 0
```

---

## State of the Art

| Old Approach (v1 Docker bot) | Current Approach (v2 LXC) | Impact |
|-------------------------------|---------------------------|--------|
| config.json `modules` list | registry.json hub-side | Auditable via Hub git history; survives `rm -rf ~/animaya` |
| Runtime pip for extensions | `bot.Dockerfile` + rebuild | Replaced entirely by LXC-native module system |
| Monolithic bot/features/ tree | modules/ directory per module | Each module self-contained with lifecycle scripts |
| _rebuild_claude_md() in dashboard/app.py | bot/modules/assembler.py | Centralised; triggered on install/uninstall/startup |

**Deprecated/outdated:**
- `bot/templates/CLAUDE.md` "Installed Modules" / "Check /data/config.json" section: this referenced the v1 Docker config.json pattern. Phase 3 replaces with registry.json + assembler. The base template text about checking config.json for module state should be updated or removed during Phase 3.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `owned_paths` should be interpreted relative to `ANIMAYA_HUB_DIR` (not module dir) | Common Pitfalls #5, Code Examples | Leakage check walks wrong paths; artifacts escape undetected |
| A2 | `depends` list should be stored in registry entry (not just manifest) to support dependents check without disk read | Architecture Patterns — Pattern 5 | Dependents check requires re-loading manifests from disk on every uninstall |
| A3 | Bridge module `owned_paths` is empty (no hub artifacts — code stays in bot/bridge/) | Code Examples | If bridge does write hub artifacts (e.g., sessions/), they would be invisible to the leakage check |
| A4 | `bot/templates/CLAUDE.md` references to `/data/config.json` for module state should be updated/removed | State of the Art | Claude's context has stale instructions pointing at non-existent config.json module list |

---

## Open Questions

1. **Where do bridge per-chat working dirs live under hub?**
   - What we know: Phase 2 D-05 says "per-chat working directories under DATA_PATH". DATA_PATH defaults to `~/hub/knowledge/animaya/`.
   - What's unclear: Are these `hub/knowledge/animaya/sessions/<chat_id>/`? If so, should `owned_paths` for the bridge module declare `sessions/`?
   - Recommendation: Planner confirms — if bridge does write to hub, declare `sessions/` in owned_paths; if sessions are ephemeral or not under hub, owned_paths stays empty.

2. **Hub knowledge/ directory initialization order**
   - What we know: `bot/main.py` creates `data_path` (`~/hub/knowledge/animaya/`) on startup. Registry lives there.
   - What's unclear: Does `setup.sh` also create this path, or is bot startup the first creator?
   - Recommendation: `registry.py:read_registry()` handles missing file gracefully (returns empty registry); `write_registry()` creates parent dirs. No ordering dependency.

3. **Semver validation strictness**
   - What we know: D-08 says `version` is a "semver str". Pydantic will accept any string.
   - What's unclear: Should Phase 3 add a regex validator to enforce semver format?
   - Recommendation: Add `pattern=r"^\d+\.\d+\.\d+.*$"` field validator in manifest.py. Loose semver check (major.minor.patch prefix) is sufficient for Phase 3.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | bot.modules package | Assumed present (Claude Box requirement) | 3.12+ | None — hard requirement |
| pydantic >=2.0 | manifest.py | NOT in pyproject.toml (must be added) | 2.13 on PyPI | None — add to deps |
| bash | install.sh / uninstall.sh | Present on all Linux systems | any | None — hard shell dependency |
| pytest >=8.0 | tests/test_modules.py | In dev deps (pyproject.toml) | >=8.0 | — |
| ~/hub/knowledge/animaya/ | registry.json | Created by bot/main.py startup | — | read_registry() handles missing |

**Missing dependencies with no fallback:**
- pydantic: must be added to pyproject.toml `[project].dependencies` before any other work

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ with pytest-asyncio 0.23+ |
| Config file | pyproject.toml `[tool.pytest.ini_options]` — `asyncio_mode = "auto"` |
| Quick run command | `python -m pytest tests/test_modules.py -x -q` |
| Full suite command | `python -m pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MODS-01 | Valid manifest.json passes pydantic validation | unit | `pytest tests/test_modules.py::TestManifest -x` | Wave 0 |
| MODS-01 | Invalid manifest (unknown field) raises ValidationError with clear message | unit | `pytest tests/test_modules.py::TestManifestReject -x` | Wave 0 |
| MODS-02 | install.sh + uninstall.sh execute without error for bridge module | integration | `pytest tests/test_modules.py::TestLifecycle -x` | Wave 0 |
| MODS-03 | Registry tracks installed module; `list_installed()` returns correct state | unit | `pytest tests/test_modules.py::TestRegistry -x` | Wave 0 |
| MODS-04 | Assembler merges base + module prompts in install order | unit | `pytest tests/test_modules.py::TestAssembler -x` | Wave 0 |
| MODS-05 | After uninstall, owned_paths are absent from filesystem | integration | `pytest tests/test_modules.py::TestLeakage -x` | Wave 0 |
| MODS-06 | No cross-module code imports (convention check) | manual | Code review + module authoring guide | — |

### Sampling Rate

- **Per task commit:** `python -m pytest tests/test_modules.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_modules.py` — covers MODS-01 through MODS-05 (test classes: TestManifest, TestManifestReject, TestRegistry, TestLifecycle, TestAssembler, TestLeakage)
- [ ] `tests/conftest.py` — add `tmp_registry`, `tmp_hub_dir`, `bridge_module_dir` fixtures (extend existing conftest.py)
- [ ] pydantic install: add `"pydantic>=2.0"` to pyproject.toml, then `pip install -e ".[dev]"`

---

## Project Constraints (from CLAUDE.md)

| Directive | Impact on Phase 3 |
|-----------|------------------|
| Python 3.12, type hints everywhere | All `bot/modules/*.py` files must have full type annotations |
| Ruff line-length 100, rules E/F/I/W | Run `ruff check bot/modules/` before commit |
| snake_case for all identifiers | registry fields: `installed_at`, `manifest_version`; function names: `install()`, `uninstall()`, `list_installed()` |
| `Path` for all filesystem paths, never string concatenation | All paths in manifest.py, registry.py, assembler.py use `Path` objects |
| Per-module logging: `logger = logging.getLogger(__name__)` | Each of `manifest.py`, `registry.py`, `assembler.py` defines its own logger |
| No runtime pip | install.sh MUST NOT run pip; any Python deps go into pyproject.toml |
| Module data in `~/hub/knowledge/animaya/` | registry.json path must be `hub_dir / "registry.json"`, configurable via DATA_PATH env var |
| Package namespace `bot` | `bot.modules.install()`, not `animaya.modules.install()` |
| Strict startup validation with `sys.exit(1)` | `bot/modules/__main__.py` should exit 1 with clear message on bad args or validation error |
| `# ──` section separators in larger files | Use in `assembler.py` and `__init__.py` where sections are distinct |

---

## Sources

### Primary (HIGH confidence)
- CONTEXT.md for Phase 3 — all locked decisions (D-01 through D-20), read directly
- REQUIREMENTS.md — MODS-01 through MODS-06 acceptance criteria, read directly
- `bot/main.py` — existing `assemble_claude_md()` stub, `DEFAULT_DATA_PATH`, startup pattern, read directly
- `tests/` directory — existing test patterns (class-based pytest, `tmp_path`, `monkeypatch`), read directly
- `pyproject.toml` — confirmed pydantic absence, confirmed dev deps, read directly

### Secondary (MEDIUM confidence)
- [CITED: docs.pydantic.dev/latest/api/config/] — `ConfigDict(extra="forbid")` API for strict model
- [VERIFIED: WebSearch] pydantic v2.13 is current stable release as of 2026-04-14

### Tertiary (LOW confidence)
- [ASSUMED] `os.replace(tmp, target)` atomic write pattern — standard POSIX practice, not verified against pydantic docs

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — pydantic v2 confirmed current; stdlib tools confirmed present
- Architecture: HIGH — all design decisions locked; patterns are direct implementations of locked decisions
- Pitfalls: MEDIUM — rollback idempotency and owned_paths path resolution are the two unresolved edge cases (Open Questions 1 and A1)

**Research date:** 2026-04-14
**Valid until:** 2026-06-14 (pydantic version stable; check if pydantic 3 releases before then)
