# Dashboard Design Doc

## Stack
- **Frontend:** Next.js 15 (App Router) + TypeScript + Tailwind CSS
- **Backend:** FastAPI (existing) — serves API endpoints the dashboard calls
- **Deployment:** Same container. Next.js built at Docker build time, served on port 3000. FastAPI on port 8090. Both behind Caddy.
- **Testing:** Playwright E2E

## Architecture

```
Caddy (animaya.makscee.ru)
├── /api/* → FastAPI :8090
└── /* → Next.js :3000
```

## Pages

### Always available (no module required):
- **Chat** `/chat` — Web chat interface, SSE streaming from Claude SDK
- **Files** `/files` — File browser + editor for /data/
- **Modules** `/modules` — Install/manage modules
- **Settings** `/settings` — Model, language, show_tools
- **Stats** `/stats` — Usage, costs, message counts, uptime
- **History** `/history` — Conversation history viewer
- **Logs** `/logs` — Live log viewer with error alerts

### Module-specific pages:
- **Spaces** `/spaces` — Visual spaces explorer (requires Spaces module)

## Module System

Modules are installable feature packs. Each module:
1. Has a definition (name, description, icon, dependencies, config fields)
2. Has an install flow (guided wizard — e.g., "paste your Telegram token")
3. Adds instructions to the bot's CLAUDE.md (appended as sections)
4. May add files to /data/ (config, templates)
5. Stores state in /data/config.json under `modules.{name}`

### Core Modules:

| Module | What it adds | Install flow |
|--------|-------------|-------------|
| **Identity** | SOUL.md, OWNER.md, onboarding prompts | Answer questions about yourself and your bot's personality |
| **Telegram** | Telegram bridge | Paste bot token from @BotFather |
| **Spaces** | Knowledge workspaces, skills | Auto — just adds CLAUDE.md instructions |
| **Memory** | 3-tier memory system | Auto — creates memory/ dir + CLAUDE.md section |
| **GitHub** | Sync /data to a GitHub repo | Connect GitHub account, select/create repo |
| **Voice** | Voice transcription | Paste Groq API key |
| **Image Gen** | Gemini image generation | Paste Google API key |
| **Self-Dev** | bot.Dockerfile management | Auto — adds CLAUDE.md section about self-dev |

### Module lifecycle:
```
Available → Installing (wizard) → Installed → Configurable
```

### Module definition format (in code):
```typescript
interface Module {
  id: string
  name: string
  description: string
  icon: string  // emoji or icon name
  category: "core" | "integration" | "feature"
  requires?: string[]  // module IDs this depends on
  configFields?: ConfigField[]  // fields shown in settings
  installSteps?: InstallStep[]  // wizard steps
}
```

## API Endpoints (FastAPI)

### Modules
- `GET /api/modules` — list all modules with install status
- `POST /api/modules/{id}/install` — start install (with config data)
- `POST /api/modules/{id}/uninstall` — remove module
- `GET /api/modules/{id}/config` — get module config
- `PUT /api/modules/{id}/config` — update module config

### Chat
- `POST /api/chat` — send message, returns immediately
- `GET /api/chat/stream` — SSE endpoint for streaming response
- `GET /api/chat/history` — conversation history

### Files
- `GET /api/files?path=` — list directory or read file
- `PUT /api/files` — write file
- `DELETE /api/files?path=` — delete file

### Settings
- `GET /api/settings` — current settings
- `PUT /api/settings` — update settings

### Stats
- `GET /api/stats` — usage stats, uptime, message counts
- `GET /api/logs?level=&limit=` — recent log entries

## UI Design Principles

- Sidebar navigation (collapsible on mobile)
- Dark mode default (with light mode toggle)
- Module badges show status (installed/available)
- Non-tech-savvy friendly: clear labels, no jargon, guided flows
- Responsive: works on mobile (bot owners check on phone)

## File Structure

```
dashboard/
├── app/
│   ├── layout.tsx          — Root layout with sidebar
│   ├── page.tsx            — Home/overview redirect
│   ├── chat/page.tsx       — Chat interface
│   ├── files/page.tsx      — File browser
│   ├── modules/page.tsx    — Module marketplace
│   ├── settings/page.tsx   — Settings
│   ├── stats/page.tsx      — Usage stats
│   ├── history/page.tsx    — Conversation history
│   └── logs/page.tsx       — Log viewer
├── components/
│   ├── Sidebar.tsx
│   ├── ModuleCard.tsx
│   ├── InstallWizard.tsx
│   ├── ChatMessage.tsx
│   ├── FileTree.tsx
│   ├── FileEditor.tsx
│   └── LogViewer.tsx
├── lib/
│   ├── api.ts              — FastAPI client
│   ├── modules.ts          — Module definitions
│   └── types.ts            — Shared types
├── next.config.ts
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```
