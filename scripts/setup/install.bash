#!/bin/bash
# Local conda environment setup script
# For Ubuntu 25.10 local development, use scripts/setup/setup_local_dev.bash instead
# This script assumes you're in an active conda environment

set -e  # Exit on error

# Check if conda environment is active
if [ -z "$CONDA_DEFAULT_ENV" ]; then
    echo "Warning: No conda environment is active."
    echo "For local development on Ubuntu 25.10, please use scripts/setup/setup_local_dev.bash"
    echo "Or activate a conda environment first: conda activate vlmaps"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Upgrade pip to latest (no longer need pip<24.1 restriction with pytorch-lightning 2.x)
echo "Upgrading pip..."
python -m pip install --upgrade pip

# Install PyTorch with CUDA 12.4 if not already installed
echo "Checking PyTorch installation..."
if ! python -c "import torch" 2>/dev/null; then
    echo "PyTorch not found. Installing PyTorch 2.5.0 with CUDA 12.4..."
    # Try conda first if available
    if command -v conda &> /dev/null; then
        conda install -y pytorch==2.5.0 torchvision==0.20.0 torchaudio==2.5.0 pytorch-cuda=12.4 -c pytorch -c nvidia
    else
        # Fallback to pip
        pip install torch==2.5.0 torchvision==0.20.0 torchaudio==2.5.0 --index-url https://download.pytorch.org/whl/cu124
    fi
else
    echo "PyTorch already installed. Verifying CUDA support..."
    python -c "import torch; print(f'PyTorch version: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}'); print(f'CUDA version: {torch.version.cuda if torch.cuda.is_available() else \"N/A\"}')"
fi

# Install Python packages from requirements.txt
echo "Installing Python packages from requirements.txt..."
pip install -r requirements.txt

# Use mamba for faster dependency solving (drop-in replacement for conda)
# If mamba is not available, falls back to conda
if command -v mamba &> /dev/null; then
    mamba install habitat-sim headless -c conda-forge -c aihabitat -y
else
    # Use conda with solver options to speed up resolution
    if command -v conda &> /dev/null; then
        conda install habitat-sim headless -c conda-forge -c aihabitat -y --solver=libmamba || \
        conda install habitat-sim headless -c conda-forge -c aihabitat -y
    else
        echo "Warning: Neither mamba nor conda found. Skipping habitat-sim installation."
        echo "Please install habitat-sim manually via conda."
    fi
fi

# Install Hierarchical-Localization
cd ~
if [ ! -d "Hierarchical-Localization" ]; then
    git clone --recursive https://github.com/cvg/Hierarchical-Localization/
fi
cd Hierarchical-Localization/

# switch to a compatible version of hloc, see the commit: https://github.com/cvg/Hierarchical-Localization/commit/936040e8d67244cc6c8c9d1667701f3ce87bf075
HLOC_COMMIT=936040e8d67244cc6c8c9d1667701f3ce87bf075
git checkout "$HLOC_COMMIT"

python -m pip install -e .
