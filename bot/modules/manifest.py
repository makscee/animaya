"""Module manifest schema (Phase 3, MODS-01).

Strict pydantic v2 model validating modules/<name>/manifest.json.
Per D-10, unknown fields are rejected; schema evolution uses manifest_version bump.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)

# ── Runtime entry namespace guard (T-08-02) ──────────────────────────
# Only bot.* dotted paths allowed — prevents arbitrary module injection
# if a manifest is ever user-supplied.
_RUNTIME_ENTRY_PATTERN = re.compile(r"^bot\.[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")

# ── Schema ──────────────────────────────────────────────────────────
# Loose semver prefix: major.minor.patch with optional pre-release/build suffix.
# Rejects strings without the three numeric segments (e.g. "not-semver", "1.2").
SEMVER_PREFIX_PATTERN = r"^\d+\.\d+\.\d+.*$"


class ModuleScripts(BaseModel):
    """Lifecycle script filenames (relative to module dir). See D-09."""

    model_config = ConfigDict(extra="forbid")

    install: str = "install.sh"
    uninstall: str = "uninstall.sh"


class ModuleManifest(BaseModel):
    """Strict pydantic model for modules/<name>/manifest.json (D-08, D-09, D-10).

    Required fields (D-08): manifest_version, name, version, system_prompt_path,
    owned_paths. Optional fields (D-09): scripts, depends, config_schema.

    Strict mode rejects unknown fields — schema evolution requires a
    manifest_version bump, not silent field addition.
    """

    model_config = ConfigDict(extra="forbid")

    manifest_version: int = Field(
        ..., ge=1, description="Schema version; currently 1"
    )
    name: str = Field(
        ..., min_length=1, description="Module name; matches folder name"
    )
    version: str = Field(
        ...,
        pattern=SEMVER_PREFIX_PATTERN,
        description="Semver-prefix version (major.minor.patch[.*])",
    )
    system_prompt_path: str = Field(
        ..., min_length=1, description="Prompt file relative to module dir"
    )
    owned_paths: list[str] = Field(
        ..., description="Files/dirs module creates (MODS-05 leakage surface)"
    )
    scripts: ModuleScripts = Field(
        default_factory=ModuleScripts,
        description="Lifecycle script filenames",
    )
    depends: list[str] = Field(
        default_factory=list, description="Other module names this depends on"
    )
    config_schema: dict | None = Field(
        default=None, description="JSON Schema passthrough for Phase 5"
    )
    runtime_entry: str | None = Field(
        default=None,
        description="Dotted Python module path (bot.*) whose module-level "
                    "on_start/on_stop callables the supervisor invokes.",
    )

    @field_validator("runtime_entry")
    @classmethod
    def _validate_runtime_entry(cls, v: str | None) -> str | None:
        """Reject paths outside the bot.* namespace (T-08-02)."""
        if v is None:
            return v
        if not _RUNTIME_ENTRY_PATTERN.match(v):
            raise ValueError(
                f"runtime_entry {v!r} must match pattern "
                f"{_RUNTIME_ENTRY_PATTERN.pattern} (only bot.* namespace allowed)"
            )
        return v


# ── Loader ──────────────────────────────────────────────────────────
def validate_manifest(module_dir: Path) -> ModuleManifest:
    """Load and validate manifest.json under module_dir.

    Args:
        module_dir: Directory containing manifest.json.

    Returns:
        Validated ModuleManifest instance.

    Raises:
        FileNotFoundError: manifest.json missing under module_dir.
        pydantic.ValidationError: schema violation (unknown field, missing
            required field, bad type, non-semver version).
        json.JSONDecodeError: manifest.json is not valid JSON.
    """
    manifest_path = module_dir / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"manifest.json missing under {module_dir}")
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = ModuleManifest.model_validate(raw)
    logger.debug("Validated manifest for %s@%s", manifest.name, manifest.version)
    return manifest
