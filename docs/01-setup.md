# 1. Setup

This guide will help you set up the VLMaps development environment. You can choose between:
- **Local Development** (recommended for Ubuntu 25.10): Set up a conda environment directly on your machine
- **Docker**: Use a containerized environment (works on any system with Docker)

## Prerequisites

### For Local Development:
- **Ubuntu 25.10** (or compatible Linux distribution)
- **NVIDIA GPU** with CUDA 12.4 support and driver 545+
- **Conda** or **Miniconda** (will be installed automatically if not present)
- **Git** installed

### For Docker:
- **Docker** and **Docker Compose** installed
- **NVIDIA GPU** with CUDA support (recommended)
- **Git** installed

## Step 1: Clone the Repository

```bash
git clone https://github.com/vlmaps/vlmaps.git
cd vlmaps
```

## Step 2: Choose Your Setup Method

### Option A: Local Development (Ubuntu 25.10)

For local development on Ubuntu 25.10, use the automated setup script:

```bash
# Make the script executable (if not already)
chmod +x scripts/setup/setup_local_dev.bash

# Run the setup script
./scripts/setup/setup_local_dev.bash
```

This script will:
- Install Miniconda if not present
- Create a conda environment with Python 3.9
- Install system dependencies (OpenGL libraries, etc.)
- Install PyTorch 2.5.0 with CUDA 12.4
- Install habitat-sim and all other dependencies
- Set up Hierarchical-Localization

After setup, activate the environment:
```bash
conda activate vlmaps
```

To verify the installation:
```bash
# Check Python version (should be 3.9)
python --version

# Check PyTorch and CUDA
python -c "import torch; print(f'PyTorch: {torch.__version__}, CUDA: {torch.version.cuda if torch.cuda.is_available() else \"N/A\"}')"

# Check habitat-sim
python -c "import habitat_sim; print('habitat-sim installed successfully')"

# Check CLIP
python -c "import clip; print('CLIP installed successfully')"
```

**Note**: For local development, you can query images, use tooling, and check for build errors more easily than in Docker.

### Option B: Docker Setup

Continue with the Docker setup steps below.

## Step 3: Data Directory

The Matterport3D dataset (~50GB) will be stored in the `data/` directory within the project. This directory is:
- Excluded from Docker builds (via `.dockerignore`)
- Excluded from Git (via `.gitignore`)
- Automatically mounted when using Docker

No additional configuration needed - the data directory will be created automatically when you download the dataset.

## Step 4: Build and Start the Container (Docker Only)

Use the provided `start.bash` script:

```bash
./scripts/docker/start.bash
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
./scripts/docker/start.bash
```

The image is automatically pulled from GitHub Container Registry: `ghcr.io/robot-autonomy-vlmaps/vlmaps:latest`

### Building Locally (Optional)

If you want to build the image locally (e.g., for development or customization):

```bash
# Set environment variable to force local build
export VLMAPS_BUILD_LOCAL=true
./scripts/docker/start.bash

# Or edit docker-compose.yml to comment out 'image:' and uncomment 'build:'
```

**Note**: Building locally takes 30-45 minutes as it installs all dependencies including habitat-sim.

## Step 5: Verify Installation

### For Local Development:
See verification steps in Option A above.

### For Docker:
All dependencies are pre-installed in the image, so you can skip `install.bash`. However, if you built locally or want to verify, check that everything is set up correctly:

```bash
# Check conda environment
conda info

# Check Python version (should be 3.9)
python --version

# Check PyTorch and CUDA
python -c "import torch; print(f'PyTorch: {torch.__version__}, CUDA: {torch.version.cuda if torch.cuda.is_available() else \"N/A\"}')"

# Check if habitat-sim is installed
python -c "import habitat_sim; print('habitat-sim installed successfully')"

# Check if other dependencies are installed
python -c "import torch; import clip; print('Dependencies OK')"
```

**Note**: If you built the image locally and dependencies aren't installed, you can run `bash scripts/setup/install.bash` inside the container. However, with the pre-built image, everything should already be installed.

### Docker OpenGL Support

The Docker image uses `nvidia/cuda` base image (not `cudagl`) with OpenGL libraries installed separately. For OpenGL rendering:

1. **X11 Forwarding** (for GUI applications):
   - The `docker-compose.yml` already configures X11 forwarding
   - Ensure X11 is accessible: `xhost +local:docker` (if needed)
   - The container mounts `/tmp/.X11-unix` and `.Xauthority` for display access

2. **Headless Rendering** (for server environments):
   - Use `xvfb` (X Virtual Framebuffer) which is pre-installed
   - Run applications with: `xvfb-run -a <your-command>`

## Container Management

### Starting the Container
```bash
./scripts/docker/start.bash
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

