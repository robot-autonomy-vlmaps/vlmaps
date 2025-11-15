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

## Step 2: Set Up Matterport3D Data Directory

Set the environment variable for where you want to store the Matterport3D dataset (~50GB). This directory will be mounted as a volume in the container.

### For Bash/Zsh:
```bash
export VLMAPS_MP3D_DATA_DIR=/path/to/your/data
```

### For Fish Shell:
```fish
set -x VLMAPS_MP3D_DATA_DIR /path/to/your/data
```

### For Permanent Setup (Bash/Zsh):
Add to your `~/.bashrc` or `~/.zshrc`:
```bash
export VLMAPS_MP3D_DATA_DIR=/path/to/your/data
```

### For Permanent Setup (Fish):
Add to `~/.config/fish/config.fish`:
```fish
set -x VLMAPS_MP3D_DATA_DIR /path/to/your/data
```

### Using Docker Compose Projects (Recommended)

Alternatively, create a `.env` file in the project root:
```bash
echo "VLMAPS_MP3D_DATA_DIR=/path/to/your/data" > .env
```

Docker Compose will automatically read this file.

## Step 3: Build and Start the Container

Use the provided `start.bash` script:

```bash
./start.bash
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
./start.bash
```

The image is automatically pulled from GitHub Container Registry: `ghcr.io/robot-autonomy-vlmaps/vlmaps:latest`

### Building Locally (Optional)

If you want to build the image locally (e.g., for development or customization):

```bash
# Set environment variable to force local build
export VLMAPS_BUILD_LOCAL=true
./start.bash

# Or edit docker-compose.yml to comment out 'image:' and uncomment 'build:'
```

**Note**: Building locally takes 30-45 minutes as it installs all dependencies including habitat-sim.

## Step 4: Verify Installation

All dependencies are pre-installed in the image, so you can skip `install.bash`. However, if you built locally or want to verify, check that everything is set up correctly:

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

**Note**: If you built the image locally and dependencies aren't installed, you can run `bash install.bash` inside the container. However, with the pre-built image, everything should already be installed.

## Container Management

### Starting the Container
```bash
./start.bash
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

