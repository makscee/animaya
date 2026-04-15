# Feature Research — v2.0 Onboarding Polish

**Domain:** Personal AI assistant platform (LXC-native, modular, Telegram + web dashboard) — onboarding polish milestone
**Researched:** 2026-04-15
**Confidence:** HIGH (grounded in shipped v1.0 code + cross-validated industry patterns)

## Scope

Four new feature areas for v2.0 (v1.0 shipped all core mechanics: bridge, modules, dashboard auth, identity/memory/git-versioning modules):

1. **Bridge-as-module** — Telegram bridge becomes installable module with token install dialog + 6-digit pairing-code owner-claim
2. **Bridge settings page** — master disable, non-owner access policy (metadata-flagged to bot), tool-use display mode (temporary DEFAULT / persistent / hidden)
3. **Identity pre-installed** — ships installed out-of-box with config file-content editor
4. **Dashboard chat + Hub file tree** — new page with inline tool-use chat panel and full `~/hub/` tree (knowledge + data)

This document REPLACES the v1.0 FEATURES.md — prior content is captured in `.planning/milestones/` audit trail.

## Table Stakes (Users Expect These)

Features users assume exist in any modern assistant install/config flow.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Token input field in install dialog | Every bot-framework install prompts for credentials (Discord, Slack, Mattermost bridges) | LOW | Reuse existing module config-form scaffolding; store in registry `config` |
| Secret redaction after save | No modern dashboard re-displays raw tokens | LOW | `••••••••1234` mask; Reveal / Rotate actions |
| "Claim ownership" pairing step | WhatsApp Web, Signal Desktop, Matrix all use short codes; users understand pattern | MEDIUM | 6-digit shown in dashboard; user messages bot; bot writes owner |
| Master on/off toggle for bridge | Zapier/n8n/IFTTT standard; emergency stop expected | LOW | Flips `bridge.enabled=false`; early-exit handler drops updates |
| Tool-use visibility in chat UI | Claude.ai, Cursor, Zed, Continue.dev all surface tool calls inline | MEDIUM | Three modes match Cursor's collapsed/expanded pattern |
| File tree in sidebar | VSCode, GitHub, Cursor, Zed — universal | MEDIUM | HTMX-friendly: lazy-load children on expand |
| File viewer for text/markdown | GitHub/GitLab/VSCode baseline | LOW | Markdown render; syntax highlight; image preview |
| Chat with streaming responses | ChatGPT/Claude.ai set baseline | MEDIUM | SSE or HTMX `sse-swap` against Claude Code SDK stream |
| "Already configured" state detection | Re-entered settings must show current state | LOW | Registry `status` drives per-state render |
| Non-owner auto-drop with logged event | `TELEGRAM_OWNER_ID` gate exists; needs UI-configurable + auditable version | LOW | Extend `_owner_gate`; emit event for log feed |

## Differentiators (Competitive Advantage)

Features that set Animaya apart from generic bot frameworks and self-hosted assistants.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Pairing-code claim with self-healing env | Users never hand-edit `.env` for `TELEGRAM_OWNER_ID` or restart systemd — bot learns owner via chat | MEDIUM-HIGH | Writes registry config; `_parse_owner_ids()` switches to config-first with env fallback |
| Non-owner access as *metadata-flag* (not just drop) | Most bots silently ignore non-owners. Animaya can let the bot *see* the message with `[from non-owner @name]:` — enables owner-curated gatekeeping logic | MEDIUM | Reuses `_envelope_message()` prefix pattern; policy enum `drop`/`flag`/`open` |
| Tool-use "temporary display" (ephemeral) | Default surfaces tool calls while active, collapses to final answer — cleaner than Cursor's always-expanded panel, more transparent than Claude.ai mobile's hidden-by-default | LOW-MEDIUM | Telegram `_on_tool_use` already implements this; port pattern to dashboard chat |
| Identity file-content editor (not form) | Edit the raw markdown that becomes the system prompt — power users get full control, casuals get sane defaults | LOW | CodeMirror/textarea in HTMX; save writes `~/hub/knowledge/animaya/identity.md`; preview "how it renders in system prompt" |
| Unified `~/hub/` tree (knowledge + workspace) | Competing assistants hide their data; Animaya exposes git-versioned state as navigable tree — trust via transparency | MEDIUM | One tree rooted at `~/hub/` spans `knowledge/`, `backlog/`, `workspace/` |
| Inline tool-use in dashboard chat matches Telegram UX | Same bot, same visible tool chain across surfaces | MEDIUM | Shared rendering; Voidnet design tokens |
| Pre-installed identity with zero-click default | Fresh install never "empty bot" — identity active from first boot, user just edits | LOW | Installer seeds registry entry + default `identity.md` |

## Anti-Features (Commonly Requested, Often Problematic)

| Anti-Feature | Why Requested | Why Problematic | Alternative |
|--------------|---------------|-----------------|-------------|
| OAuth login from bot to Telegram | Sounds "secure/modern" | Telegram has no OAuth — BotFather token IS the credential | Token paste + pairing-code owner binding |
| In-dashboard BotFather automation | "Automate full setup" | BotFather requires interactive chat + CAPTCHAs; programmatic creation violates ToS | Deep-link to `https://t.me/BotFather`; paste resulting token |
| Per-user role system (admin/editor/viewer) | "Feels professional" | This is a *personal* assistant — multi-user complicates every module | Owner + non-owner binary; `flag` policy for curated group access |
| Full web-based terminal | "Power users want it" | Duplicates Claude Code's shell tooling; LXC security nightmare | File tree + file editor + chat (shell via Claude Code tools) |
| Rich-text editor for identity | "Users hate markdown" | System prompt IS text; rich-text adds conversion bugs + HTML noise in Claude's context | Plain markdown editor with live preview |
| Hot-swap bridge token without restart | "Zero downtime" | `telegram.Application` is token-bound at build; hot-swap is semantically teardown+rebuild | Explicit restart of bridge process on token change |
| Showing every tool-use argument verbatim | "Transparency!" | Verbose JSON floods chat; defeats readability (see Claude Code issue #35932) | Summary (tool + key param); expandable "show full args" |
| UI whitelist of individual non-owner Telegram users | Convenience | Whitelists drift; non-owner `flag` policy covers 95% case | Owner claim is sticky; non-owner is drop-or-flag only |

## Feature Dependencies

```
Bridge-as-module (install dialog)
  ├── requires → v1.0 module system (validated)
  ├── requires → registry config write API (v1.0)
  └── enhances → Bridge settings page (edit after install)

Pairing-code owner-claim
  ├── requires → Bridge running (token saved) + bot reachable
  ├── requires → registry config write; in-proc reload of owner list
  └── replaces → hand-edited TELEGRAM_OWNER_ID env var

Bridge settings page
  ├── master disable       → new early-exit handler in bridge (pre-_owner_gate)
  ├── non-owner policy     → extension of _envelope_message() + _owner_gate()
  └── tool-use display mode → enhances _on_tool_use (Telegram) + new dashboard chat

Identity pre-installed + editor
  ├── requires → installer seeds registry + default identity.md
  ├── requires → file editor component (shared with Hub tree viewer)
  └── enhances → module config UX (blueprint for future module editors)

Dashboard chat + Hub tree
  ├── chat     → Claude Code SDK stream via SSE/HTMX; session cwd scoping (v1.0)
  ├── tool-use → shared tool-use display setting with Bridge
  └── tree     → path traversal guard (stay inside ~/hub/)
                 └── enhances → Identity editor (same viewer component)
```

### Dependency Notes

- **Pairing-code flow depends on bridge being up first:** install token → bridge starts → dashboard shows 6-digit → user messages bot → claim completes. Install dialog must NOT collect owner ID up-front.
- **Master disable must short-circuit BEFORE `_owner_gate`:** otherwise disabled bridges still consume Telegram updates. Add `TypeHandler` at group=-2.
- **Tool-use display mode is a single shared setting** across Telegram + dashboard chat — per-surface storage creates drift.
- **File editor is shared component** between Identity config and Hub-tree view — build once.
- **Non-owner `flag` policy must be opt-in** (default: drop) — otherwise public bot usernames leak context.

## MVP Recommendation

### Ship in v2.0 (P1)

- [ ] **Bridge module manifest + install dialog** — token input, `getMe` validation, save to registry
- [ ] **Pairing-code owner-claim** — dashboard displays 6-digit; bot recognizes `/claim XXXXXX`; writes owner; rotates code
- [ ] **Bridge settings page** — master disable, non-owner policy (`drop`/`flag`), tool-use display (`temporary`/`persistent`/`hidden`)
- [ ] **Identity pre-installed** — installer seeds registry + `~/hub/knowledge/animaya/identity.md` default
- [ ] **Identity file-content editor** — HTMX page, textarea save writes Hub file, shows system-prompt preview
- [ ] **Dashboard chat panel** — streaming, inline tool-use honoring setting, session-scoped
- [ ] **Hub file tree** — lazy-loaded tree rooted at `~/hub/`, readonly markdown/text/image viewer

### Add After v2.0 Validation (P2 / v2.x)

- [ ] File editing from Hub tree (gated on git-versioning trust)
- [ ] Pairing-code QR (`tg://resolve?domain=<bot>&text=/claim XXXXXX`)
- [ ] Tool-use argument expansion (click tool line for full JSON)
- [ ] Dashboard chat history browser

### Future Consideration (P3 / v3+)

- [ ] Per-group bridge binding (module instance per Telegram group)
- [ ] Voice input in dashboard chat (MediaRecorder → existing audio flow)
- [ ] Module marketplace
- [ ] Multi-identity switching per session/context

## Feature Prioritization Matrix

| Feature | User Value | Impl Cost | Priority |
|---------|------------|-----------|----------|
| Bridge install dialog + token save | HIGH | LOW | P1 |
| Pairing-code owner-claim | HIGH | MEDIUM | P1 |
| Bridge master disable | HIGH | LOW | P1 |
| Non-owner policy (drop/flag) | MEDIUM | LOW | P1 |
| Tool-use display mode setting | HIGH | MEDIUM | P1 |
| Identity pre-installed | HIGH | LOW | P1 |
| Identity file editor | HIGH | MEDIUM | P1 |
| Dashboard chat streaming | HIGH | MEDIUM | P1 |
| Dashboard inline tool-use render | HIGH | MEDIUM | P1 |
| Hub file tree (readonly) | HIGH | MEDIUM | P1 |
| Hub tree file editing | MEDIUM | MEDIUM | P2 |
| Tool-use argument expansion | MEDIUM | LOW | P2 |
| QR code for pairing | LOW | LOW | P3 |
| Chat history browser | MEDIUM | MEDIUM | P3 |

## Competitor / Reference Patterns

### Pairing-code UX

- **WhatsApp Web / multi-device linking:** 8-char alphanumeric or 6-digit numeric shown on secondary device; primary must be online. Animaya inverts roles (dashboard = primary, Telegram = claiming device) but mental model is identical. [WhatsApp FAQ](https://faq.whatsapp.com/1324084875126592/?cms_platform=web)
- **Discord device authorization:** short code on new device, approve in existing session. Precedent for "code shown where authenticated, confirm from other side."
- **Matrix/Element cross-signing:** emoji or numeric verification; heavier UX, same shared-secret principle.
- **Convention:** 6 digits ≈ 20 bits, fine for short-lived one-time codes with rate-limit. Rotate after use or ~5 min TTL.

### Tool-use display

- **Claude Code CLI issue #35932:** community pain point on noisy JSON per tool call; request = compact mode w/ expandable body. Validates Animaya's "temporary default." [GitHub issue](https://github.com/anthropics/claude-code/issues/35932)
- **Cursor:** collapsible cards in chat ribbon — "persistent" analog.
- **Zed assistant panel:** dimmed inline lines with tool name + target — "temporary" feel.
- **Claude.ai web:** collapsed by default with click-to-expand — "hidden" mode.
- **Animaya Telegram v1.0:** status message edits through tool states, replaced at finalize — already implements "temporary"; v2.0 formalizes as setting.

### File-tree UI

- **VSCode Explorer:** lazy-loaded tree, folder icons, inline actions — baseline.
- **GitHub web:** flat per-directory + breadcrumbs; markdown auto-renders — simpler, great for readonly.
- **Recommendation:** GitHub-style (flat per-directory, breadcrumbs, auto-render markdown) — HTMX-friendly, no JS tree lib, matches Voidnet zero-framework rule.

### Install-dialog

- **Home Assistant integrations:** step-wise (credential → validate → name → save). Validation catches 90% of token errors.
- **n8n credentials UI:** token + "Test credential" button. Animaya validates on save (single step, simpler).

## Sources

- [WhatsApp Help Center — Link device with phone number](https://faq.whatsapp.com/1324084875126592/?cms_platform=web) — HIGH confidence (official docs, 6-digit pairing UX)
- [Claude Code issue #35932 — compact display mode for MCP tool outputs](https://github.com/anthropics/claude-code/issues/35932) — HIGH confidence (validates tool-use display-mode need from Claude community)
- [WhatsApp 2026 multi-device login guide](https://sheetwa.com/blogs/whatsapp-login-phone-number-guide/) — MEDIUM confidence (third-party current-year summary)
- [Claude.ai generative UI + tool display analysis](https://michaellivs.com/blog/reverse-engineering-claude-generative-ui/) — MEDIUM confidence (practitioner reverse-engineering)
- `bot/bridge/telegram.py` — `_on_tool_use`, `_envelope_message`, `_owner_gate`, `_parse_owner_ids` already scaffold bridge-as-module mechanics
- `bot/dashboard/app.py` — token auth, module_routes hook, Jinja2 templates ready for new pages
- Animaya v1.0 validated reqs (MODS-01..06, IDEN-01..04, DASH-01..06) — HIGH confidence (shipped + tested)

## Confidence Assessment

| Area | Level | Reason |
|------|-------|--------|
| Pairing-code UX patterns | HIGH | Cross-validated (WhatsApp, Discord, Matrix); widely understood mental model |
| Tool-use display patterns | HIGH | Claude.ai/Cursor/Zed/Claude Code CLI issue converge on temporary-default |
| File-tree UI patterns | HIGH | VSCode/GitHub patterns universal; HTMX variant trivial |
| Bridge-as-module feasibility | HIGH | v1.0 module system validated all needed mechanics |
| Identity editor UX | MEDIUM | File-content-editor pattern correct, but live "how Claude sees it" preview is project-novel |
| Non-owner "flag" policy | MEDIUM | Novel; `_envelope_message` already does metadata prefixes so mechanics are natural, but user expectations less established |
