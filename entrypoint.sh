#!/bin/sh
set -e

# Configure backup schedule from env var (default: hourly at minute 8)
SCHEDULE="${BACKUP_SCHEDULE:-8 * * * *}"
echo "$SCHEDULE curl -s http://127.0.0.1:8000/api/backup > /proc/1/fd/1 2>&1" | crontab -

# Start cron
cron

# Start nginx in background
nginx &

# Start reflex backend (foreground)
exec reflex run --env prod --backend-only --backend-host 127.0.0.1
