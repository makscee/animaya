## Git Versioning Module

Everything you write under `~/hub/knowledge/` (memory files, identity files,
user notes) is auto-committed on a background interval (default every 300
seconds) by a single-committer asyncio task inside the bot process.

Implications:
- You do not need to commit manually.
- File overwrites are recoverable from git history.
- Avoid creating large binary blobs under `knowledge/` — they bloat history.
- The commit message format is `animaya: auto-commit {ISO timestamp}`.
