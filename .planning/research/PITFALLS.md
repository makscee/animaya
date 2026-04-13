# Pitfalls Research

**Domain:** Modular AI assistant platform — Telegram bridge + Claude Code SDK + LXC-native modules
**Researched:** 2026-04-13
**Confidence:** MEDIUM (mix of verified patterns from prior Animaya v1 and community sources)

## Critical Pitfalls

### Pitfall 1: Module State Leaks Across Install/Uninstall Cycles

**What goes wrong:**
A module is "uninstalled" but leaves behind config keys, cronjobs, hooks, or files in Hub knowledge/ that silently affect the still-running core or other modules. Re-installing the module finds stale state and behaves unexpectedly.

**Why it happens:**
Manifest-driven uninstall scripts are written as an afterthought. Authors list install steps but skip inverse teardown. Hub's git-versioned directory structure makes stale files invisible until they cause a bug.

**How to avoid:**
Every module manifest must declare an explicit uninstall script that is tested in isolation. Define a "clean state" contract: after uninstall, `git diff` of knowledge/ must show zero module-owned paths. Write uninstall before or alongside install, never after.

**Warning signs:**
- Module config appears in `knowledge/` after uninstall
- Re-installing a module throws "already exists" errors
- Unrelated modules start reading stale data

**Phase to address:**
Core module system phase — uninstall contract must be enforced at the manifest schema level before any modules are built.

---

### Pitfall 2: Claude Code SDK Subprocess Inherits CLAUDECODE=1

**What goes wrong:**
When Animaya is itself run inside a Claude Code session (e.g., during self-dev or testing), the SDK spawns a child Claude Code CLI process. That child inherits the `CLAUDECODE=1` environment variable from the parent and rejects the session entirely — the SDK silently hangs or errors.

**Why it happens:**
The Claude Code SDK communicates via stdin/stdout to a spawned CLI subprocess. The CLI checks `CLAUDECODE=1` to prevent recursive invocations. This is a documented known issue (anthropics/claude-agent-sdk-python issue #573).

**How to avoid:**
When spawning Claude Code SDK subprocesses, explicitly unset `CLAUDECODE` from the child environment: `env = {k: v for k, v in os.environ.items() if k != 'CLAUDECODE'}`. Always pass this sanitized env to subprocess calls.

**Warning signs:**
- SDK hangs indefinitely when testing Animaya inside a Claude Code session
- No error message, just silence from the subprocess
- Works fine when run from a plain terminal, fails inside Claude Code

**Phase to address:**
Telegram bridge / Claude Code integration phase — add env sanitization as a standard wrapper around all SDK invocations.

---

### Pitfall 3: Blocking the Telegram Event Loop on Long AI Responses

**What goes wrong:**
Claude Code responses can take 30-120 seconds. If the handler awaits the full response before returning, the bot's async event loop is blocked — no other messages are processed, Telegram retries the webhook, and duplicate responses are sent.

**Why it happens:**
Developers write `response = await claude.query(...)` inside the message handler directly. Works fine for fast APIs; fails badly for slow streaming AI calls.

**How to avoid:**
Immediately acknowledge the Telegram message (send "thinking..." or a typing indicator), then process the Claude call in a background task using `asyncio.create_task()`. Stream partial results back to the user as they arrive rather than waiting for completion.

**Warning signs:**
- Bot stops responding to new messages while processing one request
- Duplicate responses appearing (Telegram retry behavior)
- Timeout errors from Telegram webhook endpoint

**Phase to address:**
Telegram bridge phase — streaming architecture must be a design requirement, not a later optimization.

---

### Pitfall 4: Overcomplicating the Module System Early

**What goes wrong:**
The module system grows into a mini package manager with dependency resolution, version pinning, and conflict detection before any real modules exist. This complexity is wasted — the actual modules are simple and the interface is overkill.

**Why it happens:**
This is a rewrite of a Docker-based system that had complexity problems. The temptation is to "do it right this time" by designing a sophisticated system upfront. This is the same trap, different abstraction level.

**How to avoid:**
Start with the simplest possible module contract: a folder with `manifest.json`, `install.sh`, and `uninstall.sh`. No dependency graph. No version registry. Add complexity only when a real module requires it. The constraint "modules are for friends" means 5-10 modules max in v1.

**Warning signs:**
- Module manifest spec has more than 10 fields before any module is built
- Time spent on module registry/discovery before the first working module
- "What if two modules conflict?" discussions before v1

**Phase to address:**
Core module system phase — define the minimum viable manifest contract, freeze it, then build modules against it.

---

### Pitfall 5: Git Auto-Commit Conflicts in Hub knowledge/

**What goes wrong:**
Multiple processes write to Hub's `knowledge/` simultaneously — the Telegram bridge, a module's background sync, and possibly Claude Code itself. Auto-commit runs on a timer. Git detects conflicts or dirty state mid-commit, producing errors or corrupted history.

**Why it happens:**
Git is not a concurrent database. Multiple writers plus a background committer is a race condition. The prior Animaya v1 had a 300-second commit interval that masked this but didn't eliminate it.

**How to avoid:**
Single writer pattern: only one process owns git commits for `knowledge/`. Use a file lock or queue for writes. Modules write to their own scoped subdirectory (`knowledge/modules/<name>/`) and never touch other modules' paths. The git versioning module is the sole committer.

**Warning signs:**
- "Cannot lock ref" errors in git logs
- Duplicate or out-of-order commit history
- Files showing as modified immediately after commit

**Phase to address:**
Git versioning module phase — implement file-scoped write locking before enabling multi-module writes.

---

### Pitfall 6: Identity/Memory Module Prompt Injection via User Data

**What goes wrong:**
The identity module stores user-provided "who am I / who is the assistant" text directly into the system prompt. A malicious or careless user writes prompt injection into their identity config. This hijacks Claude's behavior for that session and potentially leaks system prompt content.

**Why it happens:**
It feels natural to interpolate `user_identity` string directly into f-string system prompts. The threat model for "friends only" feels low, but injection happens accidentally too (not just maliciously).

**How to avoid:**
Treat all user-provided content as data, not instructions. Use XML-tag delimiters around user-controlled content in the system prompt: `<user_identity>{content}</user_identity>`. Claude respects these boundaries much better than raw interpolation. Document this pattern as a module development convention.

**Warning signs:**
- System prompt contains raw user strings without structural delimiters
- Users can change Claude's name or persona in unexpected ways mid-conversation
- Claude "forgets" its instructions when certain memory content is loaded

**Phase to address:**
Identity module phase — establish XML-delimited system prompt assembly as the required pattern.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| In-memory conversation state | Simple, fast | Lost on restart, no audit trail | Never — Hub git state is already available |
| Hardcoded module paths | No config needed | Breaks on different Hub layouts | MVP only, must be configurable before v1 ships |
| Single global Claude session per bot | No session management | One user's long context pollutes next conversation | Never — session should be per-conversation |
| Module install via copy-paste instructions | No installer script | Can't automate, breaks on LXC reinstall | Prototyping only |
| Dashboard with no auth | Fast to build | Exposes all bot data to LAN | Never — even for friends |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Claude Code SDK | Not unsetting `CLAUDECODE=1` env var for child processes | Sanitize env before spawning SDK subprocess |
| Telegram webhooks | Not returning 200 fast enough, causing retries | Acknowledge immediately, process async |
| Telegram message edits (streaming) | Editing every token causes rate limit (30 msg/s global) | Batch edits every 0.5-1s, not per-token |
| Hub git auto-commit | Running `git commit` from multiple modules concurrently | Single committer process with write queue |
| Claude Code SDK on LXC | Assuming Claude Code CLI is on PATH after install | Verify PATH includes `~/.npm-global/bin` or wherever npx installs it |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Loading all memory files into every system prompt | Slow responses, high token cost | Load only active module summaries; full files on demand | Beyond ~5 modules with verbose state |
| Polling for new Telegram messages (getUpdates) | Higher latency, unnecessary API calls | Use webhooks in production | At any meaningful usage |
| Rebuilding system prompt from disk on every message | Disk I/O on hot path | Cache system prompt, invalidate on module config change | Immediately noticeable |
| Unbounded git history in knowledge/ | Repo grows indefinitely | Set up periodic `git gc` or shallow history policy | After ~6 months of daily use |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Exposing dashboard port (8090) directly to internet | Full bot control without Telegram auth | Tailscale-only access; Telegram Login Widget for web auth |
| Storing `CLAUDE_CODE_OAUTH_TOKEN` in module state files | Token in git history, readable by Claude itself | Only in `.env`, never written to knowledge/ |
| Module install scripts running as root | Privilege escalation if module is compromised | Run install scripts as the bot user, not root |
| Claude Code with full filesystem access | Can read/write anything on the LXC | Scope Claude's working directory; don't give it SSH keys or secrets dir |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Silent failures when a module is misconfigured | User thinks bot is broken, no idea why | Modules must emit a clear status message on load failure |
| Onboarding dumps all questions at once | Overwhelming for non-technical users | Identity module asks one question at a time, confirms before continuing |
| No indication Claude is "thinking" | Users resend messages, creating duplicate requests | Send typing action immediately, then stream partial responses |
| Module install requiring SSH access | Friends can't self-serve | Dashboard-triggered install with progress feedback |
| Memory growing silently until it breaks | User doesn't know their context is full | Active warning when core summary exceeds threshold |

## "Looks Done But Isn't" Checklist

- [ ] **Module uninstall:** Install script exists — verify uninstall script exists and leaves zero artifacts
- [ ] **Streaming bridge:** Messages arrive — verify duplicate prevention when Telegram retries webhook
- [ ] **Claude Code integration:** Queries work in terminal — verify behavior when run inside an existing Claude Code session (CLAUDECODE=1 env)
- [ ] **Git versioning:** Commits appear — verify no conflicts when Telegram handler and module sync write simultaneously
- [ ] **Dashboard auth:** Page loads — verify Telegram Login Widget actually validates the hash server-side
- [ ] **Module isolation:** Module installs — verify another module's data is not accessible or writable

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Stale module state after bad uninstall | LOW | Delete module's knowledge/ subdir, re-run uninstall, re-install |
| CLAUDECODE=1 subprocess hang | LOW | Kill hanging process, add env sanitization, redeploy |
| Corrupt git history in knowledge/ | MEDIUM | `git fsck`, restore from last clean commit, identify offending writer |
| Blocked event loop causing duplicate messages | MEDIUM | Delete duplicate messages via Telegram API, refactor handler to async |
| Identity module prompt injection | HIGH | Reset identity config, audit all memory files for injected content, review recent conversation logs |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Module state leaks on uninstall | Core module system (manifest schema) | Run install→uninstall→install cycle, check knowledge/ is clean |
| CLAUDECODE=1 subprocess inheritance | Telegram bridge / Claude Code integration | Run Animaya inside a Claude Code session, confirm no hangs |
| Blocking event loop on AI responses | Telegram bridge | Send 2 messages simultaneously, confirm both are processed |
| Over-engineered module system | Core module system (design review) | First module ships within 1 day of manifest spec being defined |
| Git commit conflicts | Git versioning module | Simulate concurrent writes, confirm no lock errors |
| Prompt injection via user data | Identity module | Write injection string as identity, confirm it doesn't alter system behavior |

## Sources

- anthropics/claude-agent-sdk-python issue #573 (CLAUDECODE=1 env inheritance bug) — HIGH confidence
- python-telegram-bot performance wiki — HIGH confidence
- Animaya v1 post-mortem (Docker complexity, blocking handlers, memory module issues) — HIGH confidence (first-hand)
- DiffMem git-based AI memory research — MEDIUM confidence
- composio.dev AI agent failure report 2026 — MEDIUM confidence
- General plugin architecture patterns (oneuptime.com, mathieularose.com) — MEDIUM confidence

---
*Pitfalls research for: Modular AI assistant platform (Animaya v2)*
*Researched: 2026-04-13*
