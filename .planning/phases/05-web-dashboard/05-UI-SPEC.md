---
phase: 5
slug: web-dashboard
status: draft
shadcn_initialized: false
preset: none
created: 2026-04-15
base_design_system: ~/hub/knowledge/voidnet/ui-spec.md
---

# Phase 5 — UI Design Contract: Web Dashboard

> Visual and interaction contract for the animaya FastAPI + Jinja2 + HTMX dashboard. Inherits from the **Voidnet Shared UI Spec** (`~/hub/knowledge/voidnet/ui-spec.md`) — that document is the authoritative source for tokens and primitives. This file defines only animaya-specific surfaces.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | none (server-rendered, no component library) |
| Base design system | Voidnet Shared UI Spec §1–§10 (LOCKED) |
| Preset | not applicable |
| Component library | hand-rolled primitives copied from voidnet-api `admin/style.css` |
| Templating | Jinja2 (FastAPI `Jinja2Templates`) |
| Interactivity | HTMX via CDN `<script src="https://unpkg.com/htmx.org@2.x">` |
| Icon library | none (emoji category icons only, per voidnet §8 Brand Tokens) |
| Font | System stack `-apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif` |
| CSS delivery | Single static file `bot/dashboard/static/style.css`, copied subset of voidnet `admin/style.css` |
| Dark mode | Default (only theme — dark surfaces per voidnet tokens) |

**Divergence from base spec:** none. All tokens, primitives, and HTMX conventions come from voidnet §2–§6 verbatim.

---

## Spacing Scale

Inherited from voidnet §2 Spacing scale (rem-based but multiples of 4px):

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px (.25rem) | Inline gaps inside badges, dot + label |
| sm | 8px (.5rem) | Tight gaps in `.activity-item` rows, inline controls |
| — | 12px (.75rem) | Card internal row padding, input padding |
| md | 16px (1rem) | Default nav padding, standard element gap |
| — | 20px (1.25rem) | `.panel-header` x-padding |
| lg | 24px (1.5rem) | Section gap, nav gap, panel margin-bottom |
| xl | 32px (2rem) | Auth card padding |
| 2xl | 48px (3rem) | Hero top padding on `/login` |

**Exceptions:** The 12px and 20px voidnet values are retained (not forced to the 4/8/16/24 pure scale) because they come from the LOCKED base spec.

---

## Typography

Inherited from voidnet §2 Typography. Animaya dashboard declares exactly 4 sizes, 2 weights:

| Role | Size | Weight | Line Height | Color token |
|------|------|--------|-------------|-------------|
| Body | 16px (1rem) | 400 | 1.5 | `--text-primary` #e0e0e0 |
| Small / label | 14px (.85rem) | 400 | 1.5 | `--text-muted` #aaa |
| Micro (stat label, badge, timestamp) | 12px (.75rem, uppercase, letter-spacing .05em) | 500 | 1.3 | `--text-faint` #666 |
| H1 hero | 32px (2rem) | 700 | 1.2 | gradient text-fill `linear-gradient(135deg, #667eea, #764ba2)` |
| H2 section | 21px (1.3rem) | 600 | 1.3 | `--text-secondary` #ccc |
| H3 panel subhead | 16px (1rem, uppercase, letter-spacing .05em) | 500 | 1.3 | `--text-dim` #888 |

**Monospace** (for JSON config preview, job stderr excerpt, events.log entries): `ui-monospace, SFMono-Regular, Menlo, Consolas, monospace`, 13px, 1.4 line-height.

---

## Color

Inherited from voidnet §2 Colors. 60/30/10 split:

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | `--bg-base` #0a0a0f | Page background, `<input>` field background |
| Secondary (30%) | `--bg-card` #12121a, `--bg-raised` #1a1a24, `--bg-nav-active` #1e1e2e | Panels, cards, buttons, active nav item |
| Accent (10%) | `--accent` #667eea (+ `--accent-deep` #764ba2 for H1 gradient) | See reserved-for list below |
| Destructive | `--err` #f87171 on `--err-bg` #2d1515 | Uninstall confirmation, failure banners, `.btn-danger` |
| Success | `--ok` #4ade80 on `--ok-bg` #152d15 | Install success, `.btn-success`, "running" status dot |
| Warning (pending) | `--warn` #eab308 on `--warn-bg` #2d2d15 | Job `status: running` pending badge |

**Accent reserved for:**
1. Primary CTA hover border on `.btn` (e.g. "Save config", "Install" before click)
2. H1 gradient text-fill (dashboard header, `/login` hero)
3. Active nav tab underline/background (`nav a.active`)
4. Stat values (`.stat-value` — e.g. "events today", "installed modules count")
5. `:focus-visible` outline on all form inputs
6. Link hover color

**Accent is NOT used for:** regular body text, inactive nav, card borders, default button fill.

---

## Copywriting Contract

### Page titles
| Page | Title | H1 |
|------|-------|-----|
| `/login` | "Sign in — Animaya" | "Animaya" (gradient) + subtitle "Sign in with Telegram" |
| `/` | "Dashboard — Animaya" | "Dashboard" |
| `/modules` | "Modules — Animaya" | "Modules" |
| `/modules/{name}` | "{Module title} — Animaya" | "{Module title}" |

### Primary CTAs
| Context | Label |
|---------|-------|
| Login screen | "Log in with Telegram" (widget default; not customized) |
| Module card (available) | "Install" |
| Module card (installed) | "Uninstall" (danger style) |
| Module detail (config form) | "Save config" |
| Logout link | "Log out" |

### Empty states
| Surface | Heading | Body |
|---------|---------|------|
| No events on `/` activity feed | "No activity yet" | "Events appear here once the bot receives messages or you install a module." |
| No installed modules on `/modules` | "No modules installed" | "Browse available modules below and click **Install** to add capabilities." |
| No available modules on `/modules` | "No modules available" | "All modules in `bot/modules/*/` are installed. Add new module folders to extend." |
| No config schema on `/modules/{name}` | "This module has no configuration" | "Nothing to configure — install/uninstall it from the Modules page." |
| No recent errors on `/` | "No recent errors" | (no body — just the heading inside the "Recent errors" panel) |

### Error states
| Situation | Copy |
|-----------|------|
| Login hash invalid | "Sign-in failed" / "Telegram verification failed. Try again or check that your system clock is correct." |
| Owner not in allowlist | "Access denied" / "This dashboard is restricted to the bot owner. Contact the operator if you think this is wrong." |
| Install failed | Banner: "Install failed: {module_name}" — expandable `<details>` with last 50 lines of combined stderr/stdout. Rollback badge: "rollback: clean" (green) or "rollback: dirty — {count} paths leaked" (red). |
| Uninstall failed | Banner: "Uninstall failed: {module_name}" — same `<details>` treatment. Rollback badge omitted (no rollback on uninstall). |
| Concurrent install (409) | Toast-style banner: "Another module operation is in progress. Wait for it to finish, then try again." |
| Config validation error | Inline under the offending field: "{JSON Schema validator message}" — e.g. "Must be at least 1" / "Must match pattern: ^[a-z]+$" |
| Config save succeeded | Green `.success` box above form: "Saved. CLAUDE.md rebuilt." |
| systemctl unavailable | Status dot grey, label "unknown — systemctl not available" |
| Session expired | Redirect to `/login`, flash message: "Your session expired. Sign in again." |

### Destructive action confirmations
| Action | HTMX `hx-confirm` text |
|--------|------------------------|
| Uninstall module | "Uninstall {module_name}? This will remove all files under its owned_paths and rebuild CLAUDE.md." |
| Log out | (no confirm — single click logs out) |

### Status wording
| State | Label | Badge variant |
|-------|-------|---------------|
| Bot process running | "Running" | `.badge-green` + `.dot.dot-green` |
| Bot process stopped | "Stopped" | `.badge-red` + `.dot.dot-red` |
| Bot process unknown | "Unknown" | `.badge-gray` + `.dot.dot-gray` |
| Install job `running` | "Installing…" | `.badge.pending` (warn yellow) |
| Install job `done` | "Installed" | `.badge-green` |
| Install job `failed` | "Failed" | `.badge-red` |

### Event log level labels
- `info` → no badge, `--text-muted` color
- `warn` → `.badge` warn yellow, uppercase "WARN"
- `error` → `.badge-red`, uppercase "ERROR"

---

## Page Topology & Component Composition

Each animaya page is a Jinja template that `{% extends "base.html" %}` with slots for `{% block title %}`, `{% block nav_active %}`, `{% block content %}`.

### Base layout (`base.html`)
```
<body>
  <div class="container">
    <h1>Animaya</h1>                  {# gradient text-fill per voidnet §2 #}
    <nav>
      <a href="/" class="{{ 'active' if nav_active=='home' }}">Dashboard</a>
      <a href="/modules" class="{{ 'active' if nav_active=='modules' }}">Modules</a>
      <a href="/logout">Log out</a>
    </nav>
    {% block content %}{% endblock %}
  </div>
</body>
```
Primitives: `.container` (max-width 1200px), `nav` + `nav a.active` per voidnet §3 Layout.

### `/login` (unauthenticated)
- Uses narrow `.login-box` (max-width 360px, margin 15vh auto) per voidnet §4 Auth.
- `.card` wraps the Telegram Login Widget `<script>` (data-size="large", `data-userpic="false"`, `data-onauth` form post to `/auth/telegram`).
- Above widget: H1 "Animaya" gradient, subtitle "Sign in with Telegram" in `--text-dim`.
- Error box `.error` above card when redirected with `?error=…`.

### `/` (dashboard home)
Three stacked panels inside `.container`:
1. **Status strip** — `.stats` flex row with 3 `.stat` cards:
   - `stat-value` = "Running/Stopped/Unknown" + dot; `stat-label` = "Bot status"
   - `stat-value` = installed module count; `stat-label` = "Modules installed"
   - `stat-value` = event count last 24h; `stat-label` = "Events today"
   - Whole strip wrapped in `<div id="status-strip" hx-get="/fragments/status" hx-trigger="every 5s" hx-swap="outerHTML">`
2. **Recent activity** — `.panel`, `.panel-header` "Recent activity", body = up to 50 `.activity-item` rows (level dot + source tag + message + timestamp nowrap). Polled with `hx-trigger="every 5s"` wrapping the activity list only.
3. **Recent errors** — `.panel`, `.panel-header` "Recent errors", body filtered to `level == "error"` from same events.log. Same polling cadence.

### `/modules`
Two panels inside `.container`:
1. **Installed modules** — `.panel` "Installed", body = CSS grid `grid-template-columns: repeat(auto-fill, minmax(350px, 1fr))`, each cell a `.card` with:
   - H3 module title (uppercase micro)
   - `.badge-green` "installed" + version tag
   - description paragraph (body text)
   - row: `<a class="btn" href="/modules/{name}">Configure</a>` + `<button class="btn btn-danger" hx-post="/modules/{name}/uninstall" hx-confirm="…" hx-target="#status-toast" hx-swap="innerHTML">Uninstall</button>`
2. **Available modules** — same grid, each card has `<button class="btn btn-success" hx-post="/modules/{name}/install" hx-target="closest .card" hx-swap="outerHTML">Install</button>`
   - When job starts, HTMX swaps the card body to a job-poll fragment (see Job polling below).

### `/modules/{name}` (detail + config)
Single `.panel` with:
- `.panel-header` = module title + status badge
- Body section 1: static metadata (version, description, `owned_paths` list)
- Body section 2: **Config form** (see Config Form Renderer below) — only present if `manifest.config_schema` is non-null
- Body section 3: **Job log** — only during active install/uninstall, populated by polling fragment
- Footer row: `<button class="btn btn-danger">Uninstall</button>` (repeats from module list for convenience) + back link

### `/logout`
No template — clear cookie, redirect to `/login`.

---

## Config Form Renderer Contract (DASH-06)

Per CONTEXT.md D-11..D-14. Renders a `config_schema` (JSON Schema subset) into an HTMX form.

### Schema → HTML input mapping

| JSON Schema type | HTML input | Annotations consumed |
|------------------|-----------|----------------------|
| `{"type": "string"}` | `<input type="text">` | `title`, `description`, `default`, `minLength`, `maxLength`, `pattern` (server-validated only) |
| `{"type": "string", "enum": [...]}` | `<select>` with `<option>` per enum value | `title`, `description`, `default` |
| `{"type": "integer"}` | `<input type="number" step="1">` | `title`, `description`, `default`, `minimum`, `maximum` |
| `{"type": "number"}` | `<input type="number" step="any">` | `title`, `description`, `default`, `minimum`, `maximum` |
| `{"type": "boolean"}` | `<input type="checkbox">` (rendered alongside label, not above) | `title`, `description`, `default` |
| **Any other type** (`object`, `array`, `$ref`, `anyOf`, …) | NOT rendered — replaced by a muted `.error`-style notice: "Unsupported schema for `{field}` — edit via CLI: `animaya-modules config {module} {field} <value>`" | — |

### Coercion rules (server-side, before jsonschema validation)
- `integer` / `number`: empty string → remove key from payload (so `default` applies); else `int(value)` / `float(value)`. On coercion error → inline message "Must be a number" before jsonschema runs.
- `boolean`: checkbox present in form-data → `True`; absent → `False`. (HTML checkboxes omit unchecked values.)
- `string` + `enum`: compared as-is to enum values; jsonschema rejects mismatches.
- Missing required field: jsonschema returns standard error message → rendered inline.

### Field layout
Each field wrapped in a `<div class="field">`:
```
<label for="cfg-{key}">{title or key}</label>
<input ...>                              {# or select, or checkbox #}
<small class="field-help">{description}</small>        {# only if description present #}
<small class="field-error">{error}</small>              {# only on validation failure, color --err #}
```

### Form mechanics
- `<form hx-post="/modules/{name}/config" hx-swap="outerHTML" hx-target="this">`
- Submit button: `<button class="btn" style="border-color:var(--accent);color:var(--accent)">Save config</button>` (primary look — uses accent reserved usage #1)
- On validation error, server re-renders the **entire form fragment** with `.field-error` populated and an `.error` box at top: "Please fix {N} error(s) below." No partial per-field swap.
- On success, server returns a `.success` box "Saved. CLAUDE.md rebuilt." followed by the fresh form (re-rendered from persisted config). `hx-swap="outerHTML"` replaces the whole form.

---

## Install/Uninstall Job UX (DASH-05)

### Flow
1. User clicks `.btn-success` "Install" on a module card.
2. Button sends `hx-post="/modules/{name}/install"` → server enqueues job, returns a fragment:
   ```html
   <div class="card job-running"
        hx-get="/modules/{name}/job/{job_id}"
        hx-trigger="every 1s"
        hx-swap="outerHTML">
     <h3>{module_name}</h3>
     <span class="badge pending">Installing…</span>
     <div class="progress"><div class="progress-bar progress-indeterminate"></div></div>
   </div>
   ```
3. Each poll returns the same fragment until `status in {done, failed}`.
4. On `done`: fragment returned is a normal "installed" module card (green badge, Uninstall button) — HTMX stops polling because the new fragment has no `hx-trigger`.
5. On `failed`: fragment returned is:
   ```html
   <div class="card job-failed">
     <h3>{module_name}</h3>
     <div class="error">
       Install failed: {module_name}
       <span class="badge {rollback_variant}">rollback: {clean|dirty}</span>
     </div>
     <details>
       <summary>Show last 50 log lines</summary>
       <pre class="job-log">{tail}</pre>
     </details>
     <button class="btn">Retry</button>
   </div>
   ```

### Concurrency (409)
If any install/uninstall is already running, server returns HTTP 409 with fragment:
```html
<div class="error" id="status-toast">Another module operation is in progress. Wait for it to finish, then try again.</div>
```
HTMX target `#status-toast` (a dedicated `<div>` in base.html above nav); auto-dismisses on next successful action.

### Progress bar
Uses voidnet §3 Progress bars primitive (height 4px, track `--border-subtle`, fill `--accent`). New `.progress-indeterminate` modifier = CSS animation sweeping 20% bar left-to-right (1.5s linear infinite). Animaya-specific extension; defined in animaya stylesheet.

---

## Activity Feed Component

Each event in `events.log` renders as an `.activity-item` row (voidnet §3):

```
<div class="activity-item">
  <span class="dot dot-{level_color}"></span>
  <span class="event-source">{source}</span>
  <span class="event-msg">{message}</span>
  <span class="event-ts">{relative_time}</span>
</div>
```

- Level → dot color: `info`→gray, `warn`→yellow (extend `.dot` with `.dot-warn` class), `error`→red.
- Source styled as `.badge-gray` .75rem uppercase.
- Timestamp rendered relative ("2m ago", "yesterday") via a Jinja filter, with full ISO as `title=` attribute for hover.

---

## HTMX Conventions (inherited from voidnet §6)

- **Polling fragments** use `hx-trigger="every {N}s"` — 5s for idle status/activity, 1s for in-flight job.
- **Stop-polling** pattern: final fragment omits `hx-trigger`.
- **Form submit**: `hx-post`, `hx-swap="outerHTML"`, `hx-target="this"` (the form itself).
- **Destructive confirm**: `hx-confirm="…"` on uninstall button.
- **Loading indicator**: `.htmx-indicator` class with opacity transition (CSS provided by voidnet base).
- **No `hx-boost`** — per CONTEXT.md D-16, full page loads on navigation.

---

## Accessibility Commitments

Inherited from voidnet §7 + animaya-specific:

- All form inputs have `<label for=…>` matching `id`.
- Checkbox labels wrap the input to expand click target.
- `:focus-visible` shows `border-color: var(--accent)` + 2px accent outline on all `<button>`, `<a>`, `<input>`, `<select>`.
- Keyboard: all HTMX-triggered actions reachable via buttons/links (no `hx-trigger="click"` on non-interactive elements).
- `<table>` not used in Phase 5 (module cards are the primary list UI). Activity feed uses `<div role="list">` with `role="listitem"` on each row for SR semantics.
- Status dot has `aria-label="{status}"` for screen readers; visible label text repeats the state.
- Job polling region has `aria-live="polite"` so status changes are announced.
- Telegram Login Widget is an `<iframe>` — we expose a visible "Sign in with Telegram" heading above it and do not rely on the widget's internal label alone.

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | none | not applicable (no shadcn) |
| Third-party registries | none | not applicable |

No component library is installed. All primitives are hand-written CSS copied from voidnet `admin/style.css` into `bot/dashboard/static/style.css`. No supply-chain surface beyond the HTMX CDN script (pinned to a specific version — planner decides pin) and the Telegram Login Widget script (`https://telegram.org/js/telegram-widget.js`, required by spec).

**Subresource Integrity:** planner should add `integrity="sha384-…"` attributes to both external scripts during implementation.

---

## Static Asset Inventory

```
bot/dashboard/
├── static/
│   ├── style.css          # Copied subset of voidnet admin/style.css + animaya extensions
│   └── favicon.svg        # Gradient "A" mark, accent #667eea (per voidnet §8)
└── templates/
    ├── base.html          # Container, nav, status-toast slot
    ├── login.html         # Telegram Login Widget
    ├── home.html          # / — status strip + activity + errors
    ├── modules.html       # /modules — installed + available grids
    ├── module_detail.html # /modules/{name} — config form + metadata
    └── _fragments/
        ├── status_strip.html
        ├── activity_feed.html
        ├── error_feed.html
        ├── module_card.html
        ├── module_card_running.html
        ├── module_card_failed.html
        ├── config_form.html
        └── config_form_saved.html
```

---

## Component Composition Summary (for planner + executor)

| Surface | Primitives used | Polling? |
|---------|-----------------|----------|
| `/login` card | `.login-box`, `.card`, H1 gradient, `.error` | no |
| `/` status strip | `.stats`, `.stat`, `.dot`, `.badge-*` | 5s |
| `/` activity feed | `.panel`, `.panel-header`, `.activity-item`, `.dot`, `.badge-gray` | 5s |
| `/` recent errors | `.panel`, `.activity-item`, `.dot.dot-red`, `.badge-red` | 5s |
| `/modules` cards | `.card`, H3 uppercase, `.badge-green`, `.btn`, `.btn-success`, `.btn-danger`, CSS grid | 1s (only during job) |
| `/modules/{name}` config form | `.panel`, `<label>`, `<input>`/`<select>`/checkbox, `.error`, `.success`, `.btn` (accent override) | no |
| Job in-flight fragment | `.card`, `.badge.pending`, progress bar + `.progress-indeterminate` | 1s |
| Job failed fragment | `.card`, `.error`, `<details>`, `<pre>`, `.badge-red` or `.badge-green` | no |
| 409 conflict toast | `.error` in `#status-toast` slot | no |

---

## Out of Scope for Phase 5 UI

Per CONTEXT.md `<deferred>` and D-23:
- Chat surface — Telegram is the chat UI for v1 (no SSE, no message list, no input form).
- Dedicated settings page (env var view, bot token masking, dashboard token rotation) — not in DASH-01..06.
- Full logs/journalctl viewer — only the events.log tail feeds activity/errors on `/`.
- File browser — dropped.
- Multi-tenant or team views — out of scope.
- Dark/light theme toggle — dark-only per voidnet spec.

(Additional-context block requested settings / logs / chat surfaces, but CONTEXT.md D-23 explicitly excludes them from Phase 5. Recorded here as deferred; will revisit in a later phase.)

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending

---

## Pre-Population Provenance

| Field group | Source |
|-------------|--------|
| Stack, primitives, tokens, HTMX conventions | `~/hub/knowledge/voidnet/ui-spec.md` §1–§10 |
| Auth / session / allowlist copy | CONTEXT.md D-01..D-04 |
| Polling cadence (5s / 1s) | CONTEXT.md D-05..D-06 |
| Install UX, 409 concurrency, rollback badge | CONTEXT.md D-07..D-10 |
| Config form types + validation + apply | CONTEXT.md D-11..D-14 |
| Page topology (multi-page URLs) | CONTEXT.md D-15..D-16 |
| Status source, event log, activity | CONTEXT.md D-17..D-21 |
| Drop v1 CORS/SSE/chat endpoints | CONTEXT.md D-22..D-23 |
| Requirements DASH-01..06 | REQUIREMENTS.md |
| Success criteria (auth→home, module install visible, config form round-trip) | ROADMAP.md Phase 5 |
| JSON Schema field renderer, coercion rules | RESEARCH.md Pattern 4 + Pitfall 1 |
| CLAUDE.md Python/HTMX conventions | `/Users/admin/hub/workspace/animaya/CLAUDE.md` |

No user questions asked — all design contract fields were answered by upstream artifacts and the shared voidnet spec.
