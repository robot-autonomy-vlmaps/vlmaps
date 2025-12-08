# 1. Setup

This guide will help you set up the VLMaps development environment using Docker.

## Prerequisites

- **Docker** and **Docker Compose** installed
- **NVIDIA GPU** with CUDA support (recommended)
- **Git** installed

## Step 1: Clone the Repository

```bash
git clone https://github.com/vlmaps/vlmaps.git
cd vlmaps
```

## Step 2: Prepare the Data Directory

Dataset files now live inside the repository under `data/`. The download script will create and populate this folder for you, so no environment variables or extra mounts are required. Ensure you have ~50GB free in the repo location.

## Step 3: Build and Start the Container

Use the provided `scripts/start.bash` script:

```bash
./scripts/start.bash
```

Or manually with docker-compose:

```bash
docker-compose up -d
docker-compose exec vlmaps bash
```

### Using Pre-built Image (Recommended - Faster)

The project provides a pre-built Docker image with all dependencies pre-installed. This is much faster (5 minutes vs 45 minutes):

```bash
# The docker-compose.yml automatically uses the pre-built image
./scripts/start.bash
```

The image is automatically pulled from GitHub Container Registry: `ghcr.io/robot-autonomy-vlmaps/vlmaps:latest`

### Building Locally (Optional)

If you want to build the image locally (e.g., for development or customization):

```bash
# Set environment variable to force local build
export VLMAPS_BUILD_LOCAL=true
./scripts/start.bash

# Or edit docker-compose.yml to comment out 'image:' and uncomment 'build:'
```

**Note**: Building locally takes 30-45 minutes as it installs all dependencies including habitat-sim.

## Step 4: Verify Installation

All dependencies are pre-installed in the image, so you can skip `scripts/install.bash`. However, if you built locally or want to verify, check that everything is set up correctly:

```bash
# Check conda environment
conda info

# Check Python version (should be 3.8)
python --version

# Check if habitat-sim is installed
python -c "import habitat_sim; print('habitat-sim installed successfully')"

# Check if other dependencies are installed
python -c "import torch; import clip; print('Dependencies OK')"
```

**Note**: If you built the image locally and dependencies aren't installed, you can run `bash scripts/install.bash` inside the container. However, with the pre-built image, everything should already be installed.

## Container Management

### Starting the Container
```bash
./scripts/start.bash
```

### Stopping the Container
```bash
docker-compose stop
```

### Restarting the Container
```bash
docker-compose restart
```

### Removing the Container
```bash
docker-compose down
```

### Viewing Container Logs
```bash
docker-compose logs vlmaps
```

## Troubleshooting

### Container won't start
- Ensure Docker is running: `docker ps`
- Check if port conflicts exist
- Verify GPU access: `nvidia-smi` (if using GPU)

### Permission errors
- Ensure your user is in the `docker` group: `sudo usermod -aG docker $USER`
- Log out and log back in after adding to docker group

### Build fails
- Check internet connection (needs to download base images)
- Ensure sufficient disk space (several GB needed)
- Check Docker logs: `docker-compose logs`

### Conda environment not activating
- The environment should auto-activate via `.bashrc`
- Manually activate: `conda activate vlmaps`

## Next Steps

Once setup is complete, proceed to:
- **[02 - Download MP3D Dataset](02-download-mp3d.md)**

