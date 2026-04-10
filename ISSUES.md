# Issues to create in Vibe Kanban

## Dashboard Polish
1. **dashboard: Add Telegram Login Widget auth** — Protect dashboard with Telegram OAuth, link session to bot owner
2. **dashboard: Implement log capture and viewer** — Python MemoryHandler → API → live log page with level filter, error alerts
3. **dashboard: Spaces visualizer page** — Visual tree of @spaces with file counts, last activity, quick navigation
4. **dashboard: Mobile responsive layout** — Collapsible sidebar, touch-friendly buttons, test on phone

## Bot Features
5. **bot: Rollback UI for git module** — Show git history in dashboard, allow revert to any commit
6. **bot: GitHub sync module implementation** — Actual git remote push/pull on install, SSH key generation
7. **bot: Telegram module install flow** — Restart bot with new token from dashboard without container rebuild
8. **bot: bot.Dockerfile viewer in dashboard** — Show current customizations, rebuild trigger button

## Platform (Phase 3)
9. **platform: Control plane for multi-tenant** — Docker API bot lifecycle management (create/start/stop/restart/delete)
10. **platform: Caddy auto-configuration** — Add/remove reverse proxy routes when bots are created/deleted

## Voidnet Integration (Phase 4)
11. **voidnet: User account linking** — Shared auth between Voidnet portal and Animaya dashboard
12. **voidnet: Boosty billing integration** — Subscription checks, usage limits, payment status
