#!/bin/bash
# Local development environment setup script for Ubuntu 25.10
# Sets up conda environment with PyTorch 2.5.0 (CUDA 12.4) and all dependencies

# Parse command line arguments
SKIP_SYSTEM_DEPS=true
if [[ "$1" == "--install-system-deps" ]] || [[ "$1" == "-i" ]]; then
    SKIP_SYSTEM_DEPS=false
fi

echo "=== VLMaps Local Development Environment Setup ==="
echo "This script will set up a conda environment for local development on Ubuntu 25.10"
echo ""
echo "Usage: $0 [--install-system-deps|-i]"
echo "  --install-system-deps, -i    Install system dependencies (optional)"
echo ""

# Check if running on Ubuntu
if [ ! -f /etc/os-release ]; then
    echo "Error: Cannot detect OS. This script is designed for Ubuntu 25.10."
    exit 1
fi

# Detect conda installation
CONDA_BASE=""
if [ -d "$HOME/miniconda3" ]; then
    CONDA_BASE="$HOME/miniconda3"
elif [ -d "$HOME/anaconda3" ]; then
    CONDA_BASE="$HOME/anaconda3"
elif [ -d "/opt/conda" ]; then
    CONDA_BASE="/opt/conda"
elif command -v conda &> /dev/null; then
    CONDA_BASE=$(conda info --base)
else
    echo "Conda not found. Installing Miniconda..."
    curl -L -o /tmp/miniconda.sh https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
    chmod +x /tmp/miniconda.sh
    /tmp/miniconda.sh -b -p "$HOME/miniconda3"
    CONDA_BASE="$HOME/miniconda3"
    rm /tmp/miniconda.sh
    echo "Miniconda installed at $CONDA_BASE"
fi

# Initialize conda for bash
source "$CONDA_BASE/etc/profile.d/conda.sh"

# Install mamba if not available (faster dependency resolution)
if ! command -v mamba &> /dev/null; then
    echo "Installing mamba for faster dependency resolution..."
    conda install -n base -c conda-forge -y mamba
fi

# Install system dependencies (OpenGL libraries for Ubuntu 25.10) - OPTIONAL
if [ "$SKIP_SYSTEM_DEPS" = false ]; then
    echo "Installing system dependencies (OpenGL libraries)..."
    echo "Note: System dependencies are optional. Use --skip-system-deps to skip this step."
    echo ""
    
    # Check if sudo is available
    if ! command -v sudo &> /dev/null; then
        echo "Warning: sudo not available. Skipping system dependencies."
        echo "You may need to install them manually if needed."
    else
        # Try to update package lists (non-fatal)
        if sudo apt-get update 2>/dev/null; then
            echo "Package lists updated successfully."
        else
            echo "Warning: Failed to update package lists. Continuing anyway..."
        fi
        
        # List of packages to try installing
        # Note: libgl1-mesa-glx is obsolete in newer Ubuntu versions, so we'll try alternatives
        PACKAGES=(
            "build-essential"
            "git"
            "git-lfs"
            "curl"
            "ca-certificates"
            "libjpeg-dev"
            "libpng-dev"
            "libglfw3-dev"
            "libglm-dev"
            "libx11-dev"
            "libomp-dev"
            "libegl1-mesa-dev"
            "libgl1-mesa-dri"
            "pkg-config"
            "wget"
            "zip"
            "unzip"
            "libxi-dev"
            "libxcursor-dev"
            "libxinerama-dev"
            "libxrandr-dev"
            "x11-apps"
            "x11-xserver-utils"
        )
        
        # Try to install packages individually, continue on failure
        INSTALLED=0
        FAILED=0
        for pkg in "${PACKAGES[@]}"; do
            if sudo apt-get install -y --no-install-recommends "$pkg" 2>/dev/null; then
                INSTALLED=$((INSTALLED + 1))
            else
                FAILED=$((FAILED + 1))
                echo "Warning: Failed to install $pkg (may not be available on this system)"
            fi
        done
        
        echo ""
        echo "System dependencies: $INSTALLED installed, $FAILED failed/not available"
        echo "Note: Missing system dependencies may cause issues with OpenGL rendering, but core functionality should work."
        echo ""
    fi
else
    echo "Skipping system dependencies installation (--skip-system-deps flag set)"
    echo ""
fi

# Create conda environment with Python 3.9 (habitat-sim requires Python 3.9)
ENV_NAME="vlmaps"
echo "Creating conda environment '$ENV_NAME' with Python 3.9..."
echo "Note: Using Python 3.9 for compatibility with habitat-sim"
if conda env list | grep -q "^${ENV_NAME} "; then
    echo "Environment '$ENV_NAME' already exists. Removing it first..."
    conda env remove -n "$ENV_NAME" -y || true
fi

conda create -n "$ENV_NAME" python=3.9 -y || {
    echo "Error: Failed to create conda environment. Exiting."
    exit 1
}
conda activate "$ENV_NAME" || {
    echo "Error: Failed to activate conda environment. Exiting."
    exit 1
}

# Configure conda channels
conda config --env --add channels conda-forge
conda config --env --set channel_priority flexible

# Install PyTorch with CUDA 12.4 via conda
echo "Installing PyTorch 2.5.0 with CUDA 12.4..."
if ! conda install -y pytorch==2.5.0 torchvision==0.20.0 torchaudio==2.5.0 pytorch-cuda=12.4 -c pytorch -c nvidia; then
    echo "Warning: Failed to install PyTorch via conda. Trying pip as fallback..."
    pip install torch==2.5.0 torchvision==0.20.0 torchaudio==2.5.0 --index-url https://download.pytorch.org/whl/cu124 || {
        echo "Error: Failed to install PyTorch. Exiting."
        exit 1
    }
fi

# Verify PyTorch installation
echo "Verifying PyTorch installation..."
python -c "import torch; print(f'PyTorch version: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}'); print(f'CUDA version: {torch.version.cuda if torch.cuda.is_available() else \"N/A\"}')" || {
    echo "Warning: PyTorch verification failed, but continuing..."
}

# Install habitat-sim via conda
echo "Installing habitat-sim..."
if command -v mamba &> /dev/null; then
    mamba install habitat-sim headless -c conda-forge -c aihabitat -y || {
        echo "Warning: Failed to install habitat-sim via mamba. Trying conda..."
        conda install habitat-sim headless -c conda-forge -c aihabitat -y --solver=libmamba || \
        conda install habitat-sim headless -c conda-forge -c aihabitat -y || {
            echo "Warning: Failed to install habitat-sim. You may need to install it manually."
        }
    }
else
    conda install habitat-sim headless -c conda-forge -c aihabitat -y --solver=libmamba || \
    conda install habitat-sim headless -c conda-forge -c aihabitat -y || {
        echo "Warning: Failed to install habitat-sim. You may need to install it manually."
    }
fi

# Upgrade pip to latest
echo "Upgrading pip..."
python -m pip install --upgrade pip

# Install Python packages from requirements.txt
echo "Installing Python packages from requirements.txt..."
cd "$(dirname "$0")"
if ! pip install -r requirements.txt; then
    echo "Warning: Some packages from requirements.txt failed to install."
    echo "You may need to install them manually or check for compatibility issues."
fi

# Install Hierarchical-Localization
echo "Installing Hierarchical-Localization..."
cd ~
if [ ! -d "Hierarchical-Localization" ]; then
    if ! git clone --recursive https://github.com/cvg/Hierarchical-Localization/; then
        echo "Warning: Failed to clone Hierarchical-Localization. Skipping..."
    fi
fi
if [ -d "Hierarchical-Localization" ]; then
    cd Hierarchical-Localization/
    HLOC_COMMIT=936040e8d67244cc6c8c9d1667701f3ce87bf075
    git checkout "$HLOC_COMMIT" || echo "Warning: Failed to checkout HLOC commit. Using current branch..."
    if ! pip install -e .; then
        echo "Warning: Failed to install Hierarchical-Localization. You may need to install it manually."
    fi
else
    echo "Warning: Hierarchical-Localization directory not found. Skipping installation."
fi

# Install vlmaps package in development mode
echo "Installing vlmaps package in development mode..."
cd "$(dirname "$0")"
pip install -e .

# Set up environment activation
echo ""
echo "=== Setup Complete ==="
echo ""
echo "To activate the environment, run:"
echo "  conda activate $ENV_NAME"
echo ""
echo "Or add this to your ~/.bashrc or ~/.zshrc:"
echo "  source $CONDA_BASE/etc/profile.d/conda.sh"
echo "  conda activate $ENV_NAME"
echo ""
echo "To verify the installation, run:"
echo "  python -c \"import torch; print(f'PyTorch: {torch.__version__}, CUDA: {torch.version.cuda if torch.cuda.is_available() else \"N/A\"}')\""
echo "  python -c \"import habitat_sim; print('habitat-sim installed successfully')\""
echo "  python -c \"import clip; print('CLIP installed successfully')\""
echo ""

