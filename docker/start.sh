#!/bin/sh
set -e

# Start Next.js dashboard in background
cd /dashboard
NODE_ENV=production npx next start -p 3000 &

# Start Python bot (FastAPI on 8090 + Telegram bridge)
cd /app
exec python -m bot
