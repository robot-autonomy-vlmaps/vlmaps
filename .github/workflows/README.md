# GitHub Actions Workflows

This directory contains CI/CD workflows for the VLMaps project.

## Workflows

### `docker-build.yml`

Automatically builds and publishes Docker images to GitHub Container Registry (ghcr.io).

**Triggers:**
- Push to `release` branch
- Pull requests targeting `release` branch (build only, no push)
- Push of version tags (e.g., `v1.0.0`)
- Manual trigger via workflow_dispatch

**What it does:**
1. Builds Docker image using the `Dockerfile`
2. Tags images appropriately:
   - `latest` - Latest build from default branch
   - `<branch-name>` - Builds from specific branches
   - `<version>` - Semantic version tags
   - `<sha>` - Git commit SHA for traceability
3. Pushes to `ghcr.io/robot-autonomy-vlmaps/vlmaps:<tag>`

**Image location:**
```
ghcr.io/robot-autonomy-vlmaps/vlmaps:latest
ghcr.io/robot-autonomy-vlmaps/vlmaps:v1.0.0
ghcr.io/robot-autonomy-vlmaps/vlmaps:trunk
```

## Usage

Workflows run automatically on push to `release` branch or when version tags are pushed. To manually trigger:

1. Go to GitHub → Actions tab
2. Select "Build and Publish Docker Image"
3. Click "Run workflow"

## Configuration

Update workflow files to:
- Change branch names
- Add additional test jobs
- Modify build triggers
- Adjust timeout values

