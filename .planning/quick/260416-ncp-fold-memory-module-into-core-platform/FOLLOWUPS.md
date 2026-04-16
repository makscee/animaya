# Pending Followups — 260416-ncp (fold memory into core)

- Expose memory consolidation knobs (`core_max_lines`, `consolidation_every_n_turns`,
  `consolidation_model`) via the dashboard settings page. Currently hardcoded to
  **150 / 10 / claude-haiku-4-5** at the call site in `bot/bridge/telegram.py` after
  this fold. Prior config schema lived in `modules/memory/manifest.json` (deleted).
