# Phase 13: Migrate dashboard frontend to shared frontend-stack-spec - Context

**Gathered:** 2026-04-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the current FastAPI + Jinja templates + `style.css` dashboard (`bot/dashboard/`) with a Next.js 15.5.15 / React 19.2.5 / Tailwind v4 / Bun app that conforms to `~/hub/knowledge/references/frontend-stack-spec.md`. Scope: every current dashboard page (home, modules, module_detail, bridge_config, login) plus the Phase 12 SSE chat + `~/hub/` file tree. No new product capabilities.

</domain>

<decisions>
## Implementation Decisions

### Backend & Deploy
- **D-01:** Next.js owns the entire public HTTP surface (SSR + route handlers + SSE). FastAPI is demoted to an internal engine process (bot runtime, Claude Code SDK bridge, module registry). No FastAPI route is reachable from outside the container after this phase.
- **D-02:** Next.js runs as a separate Bun process inside the bot container. Start script matches the spec verbatim: `next start -p 8090 -H 127.0.0.1`. Caddy / Voidnet reverse proxy keeps pointing at port 8090.
- **D-03:** Phase 12 SSE chat is served by a Next.js route handler (`/api/chat/stream` or equivalent), NOT by the current FastAPI SSE bus. The Python engine exposes a local-loopback endpoint the route handler proxies to.
- **D-04:** Next.js takes port 8090. The Python engine moves to an internal loopback port (exact number — Claude's discretion).

### Auth
- **D-05:** Auth primitive = `next-auth` `5.0.0-beta.31` (already pinned in the spec) with a custom Telegram Login Widget provider.
- **D-06:** `DASHBOARD_TOKEN` env override is preserved. Middleware checks header/query token first, falls back to the next-auth session. Required for scripted ops and token-based deploys.
- **D-07:** Owner identity is sourced from `OWNER.md` (Phase 11 output). `signIn` rejects Telegram IDs that don't match the recorded owner. No first-login-wins fallback in this phase.

### Migration
- **D-08:** Big-bang cutover. Phase ends with `bot/dashboard/templates/`, `bot/dashboard/static/`, and every FastAPI HTTP route under `bot/dashboard/*_routes.py` / `bot/dashboard/app.py` deleted or reduced to internal engine RPC only. Jinja + `itsdangerous` auth + `StaticFiles` mount all go.
- **D-09:** **ROADMAP REORDER — Phase 13 must land before Phase 12.** Phase 12 (SSE chat + Hub file tree) is then built natively in Next.js rather than in Jinja-then-ported. Roadmap order needs updating; dependencies listed for Phase 12 remain valid.
- **D-10:** Feature parity, design flexible. Every capability of the current dashboard plus the Phase 12 chat+tree is reproduced, but visual design may change where it improves UX. No new capabilities slip in under "redesign."
- **D-11:** Test surface = Playwright E2E against live `next start`. Existing pytest dashboard HTTP tests are retired as part of the cutover; pytest remains for Python engine / bot runtime.

### UI Style & Components
- **D-12:** `~/hub/knowledge/voidnet/ui-spec.md` is declared obsolete. A new shared UI style spec is authored IN this phase, extracted from `/Users/admin/hub/workspace/homelab/apps/admin` (tokens, Tailwind config, theme behavior). Target location: `~/hub/knowledge/references/ui-style-spec.md` (final name Claude's discretion). Animaya then consumes the spec from that path, same way the frontend-stack-spec is consumed today.
- **D-13:** Full Radix primitive set from the spec is installed up front (alert-dialog, avatar, dialog, dropdown-menu, label, progress, select, slot, tooltip) plus `lucide-react`. No on-demand drip.
- **D-14:** `components/ui/*` is ported from `homelab/apps/admin` verbatim (Button, Card, Dialog, Form, Input, etc.). Uses `class-variance-authority` + `tailwind-merge` + `clsx` patterns from the spec.
- **D-15:** Forms = `react-hook-form` + `zod` + `@hookform/resolvers` for all non-trivial forms (bridge_config, module config, login if it has inputs).

### Claude's Discretion
- Internal loopback port number for the Python engine.
- Exact shape of the Hub file-tree React component (tree state, dotfile toggle, expansion persistence).
- SSE reconnection strategy and tool-use inline rendering layout (constrained by Phase 12 success criteria).
- Error boundary placement and loading-state patterns.
- Whether Phase 12's owner-lock coordination lives in Next.js middleware or the engine RPC.
- Exact filename of the new shared UI style spec.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Frontend stack
- `/Users/admin/hub/knowledge/references/frontend-stack-spec.md` — pinned versions, baseline scripts, Bun/Node runtime rules, exact dependency lists. Non-negotiable for D-13, D-15.
- `/Users/admin/hub/workspace/homelab/apps/admin/` — source of truth for tokens, Tailwind config, `components/ui/*`. Read `package.json`, `tailwind.config.*`, `components/ui/*`, `app/globals.css`, theme provider wiring.

### Roadmap & requirements
- `.planning/ROADMAP.md` §Phase 8 — supervisor / lifecycle contract the new dashboard runs alongside
- `.planning/ROADMAP.md` §Phase 11 — identity pre-install → `OWNER.md` (consumed by D-07)
- `.planning/ROADMAP.md` §Phase 12 — SSE chat + Hub file tree success criteria (MUST be satisfied by this phase's Next.js build; see D-09 reorder)
- `.planning/REQUIREMENTS.md` — DASH-01..04, SEC-02, any BRDG-* that touch dashboard surfaces

### Current dashboard (what must be replaced)
- `bot/dashboard/app.py`, `bot/dashboard/*_routes.py`, `bot/dashboard/auth.py`, `bot/dashboard/forms.py`, `bot/dashboard/templates/`, `bot/dashboard/static/style.css` — enumerate every route + template + form to preserve feature parity.

### Deploy
- `docker/Dockerfile.bot` — must grow a Bun layer and the `next build` step.
- `docker/docker-compose.yml` — port 8090 routing stays; internal loopback port for FastAPI is new.
- Voidnet Caddy config (external to repo) — no change required if port 8090 remains public.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `bot/dashboard/app.py` — event bus patterns and per-user lock logic; port the coordination (not the HTTP) into engine RPC.
- `bot/dashboard/auth.py` — current Telegram Login Widget validation logic; reimplement the crypto check inside the next-auth provider callback.
- `bot/dashboard/forms.py` — schema intent for bridge_config and module config; translate to zod schemas.
- `bot/claude_query.py` — unchanged; called from engine RPC exposed to Next.js route handler.
- `homelab/apps/admin/components/ui/*` — shadcn-style primitives ready to copy (D-14).

### Established Patterns
- Jinja partials in `templates/_fragments/` correspond to future React components; map 1:1 during migration.
- HTMX-style server-rendered forms in current dashboard map cleanly to Next.js server actions or route handlers + rhf client.
- Python 3.12 engine stays; all Python → JS boundary is local HTTP (no shared runtime).

### Integration Points
- Caddy → `:8090` stays; only the process behind `:8090` changes.
- Module install/uninstall endpoints currently in FastAPI must be reachable via Next.js route handlers (which proxy or reimplement against engine RPC).
- Git auto-commit thread in `bot/features/git_versioning.py` is unaffected.

</code_context>

<specifics>
## Specific Ideas

- "Support same features but design can change if it makes sense" — parity-plus, not strict pixel parity (D-10).
- "Create a shared spec based on homelab/apps/admin; voidnet/ui-spec.md is obsolete — we need a new source of truth for UI style" — D-12 captures this; output path expected under `~/hub/knowledge/references/`.
- Scripts must match spec verbatim: `"dev": "next dev -p 8090 -H 127.0.0.1"`, `"start": "next start -p 8090 -H 127.0.0.1"`, `"test": "bun test"`.

</specifics>

<deferred>
## Deferred Ideas

- Cleanup of obsolete `~/hub/knowledge/voidnet/ui-spec.md` — separate hub-repo task; this phase only declares it obsolete.
- Post-parity visual polish iterations (motion, accessibility audit beyond Radix defaults, design-token refinements).
- Voidnet admin adopting the new shared UI style spec — their own phase.
- Migrating homelab/apps/admin onto the new shared spec file (currently it IS the source, not a consumer) — future alignment task.
- Replacing `DASHBOARD_TOKEN` bypass with a proper service-account auth model.

</deferred>

---

*Phase: 13-migrate-dashboard-frontend-to-shared-frontend-stack-spec*
*Context gathered: 2026-04-17*
