# identity module

Stores the user's self-definition (`USER.md`) and the assistant's persona
(`SOUL.md`) under `~/hub/knowledge/identity/`. Onboarding runs on first
Telegram message after install via a 3-question conversational Q&A. The
`/identity` command re-runs onboarding and overwrites both files.

## Files

- `manifest.json` — Phase 3 module manifest
- `install.sh`    — creates `~/hub/knowledge/identity/{USER.md,SOUL.md,.pending-onboarding}`
- `uninstall.sh`  — removes `~/hub/knowledge/identity/` entirely
- `prompt.md`     — static module prompt (assembler-injected once)

## owned_paths

Empty (`[]`). Identity files live OUTSIDE `ANIMAYA_HUB_DIR` (sibling
directory `~/hub/knowledge/identity/`), and Phase 3 owned_paths validation
rejects `..` segments. Cleanup is enforced by `uninstall.sh`. Phase 3
leakage check passes vacuously.

## Runtime

Bot-side onboarding state machine + query-time injection live in
`bot/modules_runtime/identity.py` (per MODS-06: modules communicate only
through hub files; bot owns module-aware code).
