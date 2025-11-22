# Scripts Directory

This directory contains all scripts organized by category for better maintainability.

## Directory Structure

```
scripts/
├── setup/          # Setup and installation scripts
├── docker/         # Docker-related scripts
├── data/           # Data management scripts
└── ci/             # CI/CD helper scripts (if any)
```

## Scripts

### Setup Scripts (`setup/`)

- **`setup_local_dev.bash`** - Local development environment setup for Ubuntu 25.10
  - Creates conda environment with Python 3.9
  - Installs PyTorch 2.5.0 with CUDA 12.4
  - Installs habitat-sim and all dependencies
  - Usage: `./scripts/setup/setup_local_dev.bash [--install-system-deps]`

- **`install.bash`** - Installation script for conda environment
  - Installs PyTorch with CUDA 12.4
  - Installs habitat-sim via conda
  - Installs Python packages from requirements.txt
  - Usage: Run inside an active conda environment

### Docker Scripts (`docker/`)

- **`start.bash`** - Start/attach to Docker development container
  - Manages docker-compose container lifecycle
  - Automatically activates conda environment
  - Usage: `./scripts/docker/start.bash [MP3D_DATA_DIR]`

### Data Scripts (`data/`)

- **`download-mp3d.bash`** - Download Matterport3D dataset
  - Downloads scene scans and habitat tasks
  - Updates configuration files
  - Usage: `./scripts/data/download-mp3d.bash [SCENE_ID]`

### CI Scripts (`ci/`)

Currently empty. Add CI/CD helper scripts here as needed.

## Usage

All scripts should be run from the project root directory:

```bash
# Setup local development environment
./scripts/setup/setup_local_dev.bash

# Start Docker container
./scripts/docker/start.bash /path/to/data

# Download dataset
./scripts/data/download-mp3d.bash
```

## Adding New Scripts

When adding new scripts:

1. Place them in the appropriate subdirectory based on their purpose
2. Make them executable: `chmod +x scripts/<category>/new_script.bash`
3. Update this README with a description
4. Update any relevant documentation

## Symlinks (Optional)

For convenience, you can create symlinks in the project root:

```bash
ln -s scripts/setup/setup_local_dev.bash setup_local_dev.bash
ln -s scripts/docker/start.bash start.bash
ln -s scripts/data/download-mp3d.bash download-mp3d.bash
```

However, it's recommended to use the full path for clarity and to avoid cluttering the root directory.

