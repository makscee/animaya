# Phase 5 Discussion Log

**Date:** 2026-04-15
**Mode:** discuss (interactive)

## Gray Area Selection

**Question:** Which gray areas for Phase 5 Web Dashboard to discuss?
**Selected:** Access & session, Liveness mechanism, Install UX & log surfacing, Config form + page topology
**Also discussed after prompt:** Status/activity content (follow-up area)

Options not taken: v1 code reuse, identity reconfigure (both resolved without dedicated discussion — see D-22/D-23 and carried_forward notes).

## Area 1: Access & Session

| Q | Options | Answer |
|---|---------|--------|
| Who can use the dashboard? | Owner-only allowlist / Any TG-authed user / No auth yet (dev) | **Owner-only allowlist** |
| Where does uvicorn bind + HTTPS? | 127.0.0.1 + Caddy TLS / 0.0.0.0 + app TLS / Claude's discretion | **127.0.0.1 + Caddy/Voidnet TLS** |
| Session/cookie mechanics? | Signed cookie 30d TTL / Signed cookie short TTL / Server-side session store | **Signed cookie, 30-day TTL** |

→ D-01, D-02, D-03, D-04

## Area 2: Liveness

| Q | Options | Answer |
|---|---------|--------|
| Refresh mechanism? | HTMX poll 5s / SSE / Poll + SSE for install / WebSocket | **HTMX polling every 5s** |
| Poll rate? | 5s idle / 1s install / Fixed 3s / N/A | **5s steady, 1s during install** |

→ D-05, D-06

## Area 3: Install UX

| Q | Options | Answer |
|---|---------|--------|
| Install click UX? | Blocking POST + redirect / Async + poll / Async + live log | **Async start + poll status** |
| Failure UI? | Error banner + stderr excerpt / Just banner / Full log dump | **Error banner + stderr excerpt** |
| Concurrency? | Single global lock, 409 / Queue / Per-module lock | **Single global lock, 409 on conflict** |

→ D-07, D-08, D-09, D-10

## Area 4: Config Form + Topology

| Q | Options | Answer |
|---|---------|--------|
| JSON Schema types? | Primitives + enum / + flat object / Full schema | **Primitives + enum only** |
| Validation? | Server-only jsonschema / HTML5 + server / Server + raw textarea | **Server-only via jsonschema** |
| URL structure? | Multi-page / Single-page tabs / hx-boost SPA | **Multi-page (/ /modules /modules/{name})** |
| Config apply? | Write + rebuild CLAUDE.md / Reconfigure hook / Save + restart | **Write config + rebuild CLAUDE.md** |

→ D-11, D-12, D-13, D-14, D-15, D-16

## Area 5: Status / Activity / Errors (follow-up)

| Q | Options | Answer |
|---|---------|--------|
| Running state source? | systemctl is-active / In-process self-report / TG API ping | **systemctl is-active** |
| Activity source? | In-mem ring buffer / journalctl tail / File-backed JSONL | **File-backed event log** |
| Errors source? | Same ring buffer / Separate error buffer / journalctl grep | **Same source as activity (filtered by level)** |
| Reconcile split? | Unified JSONL filter by level / Split file+mem / File + in-mem shadow | **Unified JSONL, filter by level** |

→ D-17, D-18, D-19, D-20, D-21

## End

User selected "Ready" → write CONTEXT.md.
