# Story 6.1: GitHub Actions Docker Build & Publish

## Status: in-progress

## Epic
Epic 6: CI/CD & Deployment

## Description
As a **developer**,
I want **GitHub Actions to build and publish a Docker image on push**,
So that **I can pull and run the app on any Docker host for real-world testing**.

## Acceptance Criteria

### AC1: GitHub Actions Workflow
- [x] Workflow triggers on push to `main` branch
- [x] Workflow builds Docker image using existing `Dockerfile`
- [x] Workflow pushes image to GitHub Container Registry (ghcr.io)

### AC2: Image Tagging
- [x] Image tagged with `latest` on every push
- [x] Image tagged with short SHA for traceability

### AC3: Docker Image Works
- [ ] Image runs with `docker run -p 3000:3000 -p 8000:8000 -v ./data:/app/data ghcr.io/<owner>/tasmo-guardian:latest`
- [ ] Data persists in mounted volume
- [ ] App accessible on port 3000

## Technical Notes

### Workflow File
```yaml
# .github/workflows/docker-publish.yml
name: Docker Build & Publish

on:
  push:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - uses: actions/checkout@v4

      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=raw,value=latest
            type=sha,prefix=

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
```

### Dockerfile Update (if needed)
Current Dockerfile may need adjustment for production:
- Ensure `reflex run --env prod` binds to `0.0.0.0`

## Dependencies
- None (uses existing Dockerfile)

## Definition of Done
- [x] `.github/workflows/docker-publish.yml` created
- [ ] Push to main triggers workflow
- [ ] Image appears in GitHub Packages
- [ ] `docker pull ghcr.io/<owner>/tasmo-guardian:latest` works
- [ ] Container runs and serves app on port 3000
