# Animaya

A personal AI assistant platform. Each user gets an isolated Claude Code-powered
assistant connected to Telegram, extensible through installable modules.

## Install

```bash
./scripts/setup.sh
```

Sets up `.venv`, writes `~/.config/systemd/user/animaya.service`, and starts the
bot under `systemctl --user`.

## Environment variables

### Phase 1 / 2 (required)

| Var | How to obtain |
|-----|---------------|
| `TELEGRAM_BOT_TOKEN` | From `@BotFather` on Telegram |
| `CLAUDE_CODE_OAUTH_TOKEN` | `claude login` (or your Claude Code OAuth flow) |

### Phase 5 dashboard (required)

The web dashboard binds to `127.0.0.1:8090` (configurable via `DASHBOARD_PORT`).
Caddy / Voidnet must terminate TLS on a public hostname and reverse-proxy to
this port.

| Var | How to obtain |
|-----|---------------|
| `SESSION_SECRET` | `openssl rand -hex 32` — generate once, keep stable |
| `TELEGRAM_OWNER_ID` | Message `@userinfobot` on Telegram |
| `TELEGRAM_BOT_USERNAME` | Your bot's username without the `@` |

### Optional

| Var | Default | Purpose |
|-----|---------|---------|
| `DASHBOARD_PORT` | `8090` | TCP port the dashboard binds on `127.0.0.1` |
| `DATA_PATH` | `~/hub/knowledge/animaya` | Hub data directory |
| `ANIMAYA_EVENTS_LOG` | `$DATA_PATH/events.log` | JSONL events feed for dashboard |

## Web Dashboard (Phase 5)

After the bot is running and Caddy is terminating TLS on your public hostname
(e.g. `animaya.example.com`), register the **Login Widget domain** with
BotFather so the Telegram Login Widget callback can authenticate you.

1. Open `@BotFather` in Telegram.
2. `/mybots` → select your bot → `Bot Settings` → `Domain`.
3. Use `/setdomain` and paste the public dashboard hostname
   (e.g. `animaya.example.com`).

Without `/setdomain` the Login Widget renders but the "Log in" button does
nothing — the Telegram script refuses to sign its callback.

## Run

```bash
python -m bot          # local development, needs .env
```

The service unit runs `run.sh`, which sources `.env` and execs `python -m bot`.
