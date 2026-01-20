# Story 6.2: Single-Port Docker with nginx

## Status: in-progress

## Epic
Epic 6: CI/CD & Deployment

## Description
As a **user deploying TasmoGuardian**,
I want **the Docker container to handle all routing internally**,
So that **I can run it with a simple port mapping without needing Traefik or complex reverse proxy config**.

## Acceptance Criteria

### AC1: Single Port Entry
- [ ] Container exposes only port 3000
- [ ] All requests (static, API, websocket, upload) work through port 3000

### AC2: nginx Internal Routing
- [ ] nginx serves static frontend files
- [ ] nginx proxies `/_event` to backend (websocket)
- [ ] nginx proxies `/api` to backend
- [ ] nginx proxies `/_upload` to backend

### AC3: Simple Docker Run
- [ ] Works with: `docker run -p 3000:3000 -v ./data:/app/data ghcr.io/tinuva/tasmoguardian:latest`
- [ ] No external reverse proxy required for basic usage

## Technical Notes

### Dockerfile Changes
```dockerfile
# Replace serve with nginx
RUN apt-get update && apt-get install -y nginx

# Copy nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Start both nginx and backend
CMD sh -c "nginx && reflex run --env prod --backend-only --backend-host 127.0.0.1"
```

### nginx.conf
```nginx
events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    
    server {
        listen 3000;
        
        # Static frontend
        location / {
            root /app/.web/build/client;
            try_files $uri $uri/ /index.html;
        }
        
        # Backend API
        location /api {
            proxy_pass http://127.0.0.1:8000;
            proxy_set_header Host $host;
        }
        
        # File upload
        location /_upload {
            proxy_pass http://127.0.0.1:8000;
            proxy_set_header Host $host;
            client_max_body_size 50M;
        }
        
        # Websocket
        location /_event {
            proxy_pass http://127.0.0.1:8000;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
        }
    }
}
```

### Updated docker-compose.example.yml
```yaml
version: '3.8'
services:
  tasmoguardian:
    image: ghcr.io/tinuva/tasmoguardian:latest
    container_name: tasmoguardian
    ports:
      - "3000:3000"
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

## Dependencies
- story-6.1 (Docker build pipeline)

## Definition of Done
- [ ] Dockerfile updated with nginx
- [ ] nginx.conf created with routing rules
- [ ] Container starts both nginx and backend
- [ ] Simple docker-compose works without Traefik
- [ ] Websocket connection works
- [ ] File upload works
- [ ] API endpoints work
