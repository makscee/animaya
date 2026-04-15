# Phase 3: Module System - Discussion Log

**Date:** 2026-04-14
**Mode:** interactive (discuss)

Audit trail of Q&A that produced `03-CONTEXT.md`. For human reference only.

---

## Gray area selection

**Q:** Which gray areas to discuss for Phase 3 (Module System)?
**Options presented:**
1. Module location & scope
2. Manifest schema shape
3. Lifecycle contract
4. CLAUDE.md assembly

**Selected:** All four.

---

## Area 1 — Module location & scope

**Q1:** Where do module folders live on disk?
- Repo + hub split (recommended)
- Hub only
- Repo only
- **Answer:** Repo only — all modules in `~/animaya/modules/`.

**Q2:** Does Phase 2 Telegram bridge become a module retroactively?
- Stays core (recommended)
- Becomes module
- Core with module shim
- **Answer:** Becomes module.

**Q3:** Where does registry.json live?
- Hub state (recommended)
- Animaya data
- Both (derived)
- **Answer:** "what registry?" — user challenged the premise.

**Q4:** How does user install/uninstall modules in Phase 3?
- Python CLI module (recommended)
- Standalone script
- Library only
- **Answer:** Library only.

### Follow-ups after "what registry?"

**Q5:** Given modules live in repo, what's source of truth for 'installed'?
- No registry file (recommended)
- Simple enabled list
- Full registry.json
- **Answer:** Full registry.json.

**Q6:** Who auto-installs bridge on fresh setup?
- setup.sh calls API (recommended)
- Auto-install on boot
- Manual step
- **Answer:** setup.sh calls API.

**Q7:** Can modules be disabled without uninstall?
- Install/uninstall only (recommended)
- Three states
- **Answer:** Install/uninstall only.

**Q8:** Where does registry.json live?
- Hub state (recommended)
- Animaya data
- **Answer:** Hub state.

---

## Area 2 — Manifest schema shape

**Q1:** Which fields in manifest.json (multi-select)?
- system_prompt_path / scripts / depends / config_schema
- **Answer:** "i'm not sure" — Claude's call: include all four (per recommendation).

**Q2:** MODS-05 — how does uninstall know what to clean?
- Declared in manifest (recommended)
- uninstall.sh trust
- Hybrid
- **Answer:** Declared in manifest (`owned_paths`).

**Q3:** How strict is pydantic validation?
- Strict + unknown rejected (recommended)
- Strict known, allow extras
- **Answer:** Strict + unknown rejected.

**Q4:** Schema versioning?
- manifest_version field (recommended)
- No schema version
- **Answer:** manifest_version field.

---

## Area 3 — Lifecycle contract

**Q1:** What does core pass to install.sh / uninstall.sh?
- Env vars (recommended)
- CLI args
- Both
- **Answer:** Env vars.

**Q2:** When does registry.json update vs install.sh?
- After success only (recommended)
- Before with rollback
- **Answer:** After success only.

**Q3:** Install failure recovery?
- Auto-rollback (recommended)
- Leave mess, log loud
- Checkpoint + resume
- **Answer:** Auto-rollback.

**Q4:** Re-installing already-installed module?
- Reject (recommended)
- No-op
- Reinstall = uninstall+install
- **Answer:** Reject.

---

## Area 4 — CLAUDE.md assembly

**Q1:** Module prompt ordering?
- Install order (recommended)
- Dep topological
- Alphabetical
- Manifest priority
- **Answer:** Install order.

**Q2:** Prompt wrapping?
- XML per module (recommended)
- Markdown heading
- Raw concat
- **Answer:** XML per module.

**Q3:** Re-assembly trigger?
- Install/uninstall hooks (recommended)
- Every bot startup
- Both (defensive)
- **Answer:** Every bot startup.

**Q4:** Output location + base prompt?
- Repo + base prepended (recommended)
- Hub + base prepended
- Repo, no base
- **Answer:** Repo + base prepended.

---

## Closure

**Q:** Covered all four; remaining candidate is MODS-06 structural enforcement. Explore or ready?
- Ready for context
- Discuss MODS-06 briefly
- **Answer:** Ready for context. MODS-06 logged as convention-only (Claude's discretion).

---

*Generated: 2026-04-14*
