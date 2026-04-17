# Phase 13: Migrate dashboard frontend to shared frontend-stack-spec - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-17
**Phase:** 13-migrate-dashboard-frontend-to-shared-frontend-stack-spec
**Areas discussed:** Backend split + deploy, Auth flow, Migration strategy, Design system reuse

---

## Backend split + deploy

### Q: Who owns HTTP surface once migration lands?
| Option | Description | Selected |
|--------|-------------|----------|
| Next.js owns it all | Next.js serves SSR + API + SSE; FastAPI demoted to internal engine | ✓ |
| FastAPI stays backend | Next.js pure UI against existing FastAPI endpoints | |
| Split by concern | Next.js renders/auth; FastAPI keeps chat/SSE/engine | |

### Q: How does Next.js ship inside the container?
| Option | Description | Selected |
|--------|-------------|----------|
| Separate bun process | `next start -p <PORT> -H 127.0.0.1` alongside uvicorn | ✓ |
| next export + FastAPI static | Static export mounted via StaticFiles | |
| Standalone Node output | `next build` standalone served by Bun | |

### Q: SSE chat source for Phase 12 going forward?
| Option | Description | Selected |
|--------|-------------|----------|
| Keep FastAPI SSE bus | EventSource points at existing FastAPI path | |
| Next.js route handler | New `/api/chat/stream` in Next.js, proxies engine | ✓ |

### Q: Port layout inside container?
| Option | Description | Selected |
|--------|-------------|----------|
| Next.js on 8090 | Python engine moves to internal loopback port | ✓ |
| Next.js on new port | FastAPI keeps 8090; Caddy routes by path | |

---

## Auth flow

### Q: Auth primitive in new dashboard?
| Option | Description | Selected |
|--------|-------------|----------|
| next-auth 5 Telegram provider | Spec-pinned `next-auth@5.0.0-beta.31` with custom TG provider | ✓ |
| Port itsdangerous session | Reimplement current signed-cookie flow in Next.js | |
| next-auth + current cookies | Shim for one release to avoid forced re-login | |

### Q: DASHBOARD_TOKEN bypass — keep?
| Option | Description | Selected |
|--------|-------------|----------|
| Keep as env override | Middleware checks token first, session fallback | ✓ |
| Drop it | Session auth only | |

### Q: Owner identity source?
| Option | Description | Selected |
|--------|-------------|----------|
| OWNER.md (Phase 11) | signIn rejects non-owner Telegram IDs | ✓ |
| First-login wins + claim FSM | Phase 9 owner-claim flow | |

---

## Migration strategy

### Q: Cutover shape?
| Option | Description | Selected |
|--------|-------------|----------|
| Big-bang | Jinja + FastAPI routes deleted at phase end | ✓ |
| Incremental, dual-mount | Migrate pages one-by-one | |

### Q: Phase 12 SSE chat — does Phase 13 block it?
| Option | Description | Selected |
|--------|-------------|----------|
| Ph12 lands in Jinja first, ported here | Phase 12 ships in Jinja, Phase 13 ports to Next.js | |
| Ph12 lands directly in Next.js | Reorder: Phase 13 before Phase 12 | ✓ |
| Build both — rewrite during Ph13 | Phase 12 in Jinja, rewrite in Ph13 | |

### Q: Parity scope — what's in Phase 13?
| Option | Description | Selected |
|--------|-------------|----------|
| Strict parity | Pixel/behavior identical | |
| Parity + light reskin | Same routes, new tokens/primitives | ✓ (via "Other") |
| Parity minus dead pages | Drop roadmap-deprecated pages | |

**User's choice:** "support same features but design can change if it makes sense"
**Notes:** Parity-plus — capability parity strict, visual design may change where it improves UX.

### Q: Test surface during migration?
| Option | Description | Selected |
|--------|-------------|----------|
| Playwright on live Next.js | E2E against `next start` in Docker | ✓ |
| Keep pytest dashboard tests | Rewrite existing tests to hit Next.js | |
| Both | Pytest for contracts, Playwright for flows | |

---

## Design system reuse

### Q: Which design tokens source wins?
| Option | Description | Selected |
|--------|-------------|----------|
| voidnet/ui-spec.md | Adopt existing shared Voidnet dark-theme tokens | |
| Mirror homelab/apps/admin | Copy admin Tailwind config verbatim | |
| Start minimal | Tailwind defaults only, polish later | |

**User's choice:** "create a shared spec based on homelab/apps/admin, voidnet/ui-spec.md is obsolete, we need a new source of truth for ui style"
**Notes:** Authors a NEW shared UI style spec extracted from homelab/apps/admin. voidnet/ui-spec.md declared obsolete. Spec lives under `~/hub/knowledge/references/`.

### Q: Radix + lucide primitives adoption?
| Option | Description | Selected |
|--------|-------------|----------|
| Full set from spec | Install all spec-listed Radix primitives + lucide-react up front | ✓ |
| On-demand | Install as needed during migration | |

### Q: shadcn-style local components?
| Option | Description | Selected |
|--------|-------------|----------|
| Copy from homelab/admin | Port `components/ui/*` verbatim | ✓ |
| Write minimal locally | Grown as needed | |

### Q: Forms/validation stack?
| Option | Description | Selected |
|--------|-------------|----------|
| react-hook-form + zod (spec) | Spec-pinned rhf + zod + @hookform/resolvers | ✓ |
| Native forms | Plain `<form>` + server actions | |

---

## Follow-up: New shared UI spec — where authored?

| Option | Description | Selected |
|--------|-------------|----------|
| Pre-req, not in Phase 13 | Authored in hub/homelab before phase starts | |
| Phase 13 authors it inline | Extract from homelab/admin + consume in same phase | ✓ |
| Phase 13 consumes admin directly | No spec file; defer authoring | |

---

## Claude's Discretion

- Internal loopback port number for Python engine
- File-tree React component internals
- SSE reconnection / tool-use render layout (within Phase 12 success criteria)
- Error boundary & loading-state patterns
- Exact filename of the new shared UI style spec

## Deferred Ideas

- Cleanup of obsolete `~/hub/knowledge/voidnet/ui-spec.md` (hub-repo task)
- Post-parity visual polish, a11y audit beyond Radix defaults
- Voidnet admin adopting the new shared UI style spec
- Migrating homelab/apps/admin onto the new shared spec file
- Replacing `DASHBOARD_TOKEN` bypass with proper service auth
