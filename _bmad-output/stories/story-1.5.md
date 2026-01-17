# Story 1.5: Docker and Standalone Deployment

## Status: complete

## Epic
Epic 1: Project Foundation & Core Data Layer

## Description
As a **developer**,
I want **Docker and standalone deployment configurations**,
So that **users can deploy TasmoGuardian in their preferred environment**.

## Acceptance Criteria
- [x] Dockerfile creates working container image
- [x] docker-compose.yml mounts `data/` volume for persistence
- [x] Container exposes port 3000
- [x] Image builds in under 5 minutes
- [x] `pip install -r requirements.txt` installs all dependencies
- [x] `reflex run` starts the application standalone
- [x] .env.example documents required environment variables

## Technical Notes

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN reflex init

EXPOSE 3000

CMD ["reflex", "run", "--env", "prod"]
```

### docker-compose.yml
```yaml
version: '3.8'
services:
  tasmoguardian:
    build: .
    ports:
      - "3000:3000"
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

### .env.example
```
# TasmoGuardian Configuration
# Copy to .env and modify as needed

# Database location (default: data/tasmobackupdb.sqlite3)
# DB_PATH=data/tasmobackupdb.sqlite3

# Backup directory (default: data/backups)
# BACKUP_DIR=data/backups
```

## Dependencies
- story-1.1

## NFRs Covered
- NFR12: Runs in Docker container
- NFR13: Runs as standalone Python application

## Definition of Done
- [x] Code complete - Dockerfile and docker-compose.yml created
- [x] Docker image builds successfully
- [x] Container runs and serves app on port 3000
- [x] Standalone installation works
- [x] .env.example documented
