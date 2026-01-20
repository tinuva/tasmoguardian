# Story 6.3: Built-in Cron Scheduling

## Status: complete

## Epic
Epic 6: CI/CD & Deployment

## Description
As a **user running TasmoGuardian in Docker**,
I want **automatic scheduled backups without external cron setup**,
So that **backups run automatically like the original TasmoBackupV1**.

## Acceptance Criteria

### AC1: Cron Runs Inside Container
- [ ] Cron daemon starts with container
- [ ] Default schedule: hourly at minute 8 (matching v1 behavior)

### AC2: Configurable Schedule
- [ ] `BACKUP_SCHEDULE` env var overrides default cron schedule
- [ ] Default: `8 * * * *` (hourly)

### AC3: Backup Endpoint Called
- [ ] Cron job calls `http://localhost:8000/api/backup`
- [ ] Logs backup results

## Technical Notes

### Dockerfile Changes
```dockerfile
# Install cron
RUN apt-get update && apt-get install -y cron

# Add cron job
RUN echo '8 * * * * curl -s http://localhost:8000/api/backup > /proc/1/fd/1 2>&1' > /etc/cron.d/tasmoguardian \
    && chmod 0644 /etc/cron.d/tasmoguardian

# Start cron with nginx and backend
CMD sh -c "cron && nginx & reflex run --env prod --backend-only --backend-host 127.0.0.1"
```

### Optional: Entrypoint for Dynamic Schedule
```bash
#!/bin/sh
SCHEDULE="${BACKUP_SCHEDULE:-8 * * * *}"
echo "$SCHEDULE curl -s http://localhost:8000/api/backup > /proc/1/fd/1 2>&1" > /etc/cron.d/tasmoguardian
chmod 0644 /etc/cron.d/tasmoguardian
cron
nginx &
exec reflex run --env prod --backend-only --backend-host 127.0.0.1
```

### Environment Variable
```yaml
environment:
  - BACKUP_SCHEDULE=8 * * * *  # Optional, defaults to hourly
```

## Dependencies
- story-6.2 (Single-port Docker with nginx)

## Definition of Done
- [ ] Cron installed in Docker image
- [ ] Default hourly backup schedule works
- [ ] `BACKUP_SCHEDULE` env var configurable
- [ ] Backup logs visible in container logs
