#!/bin/bash
python -m pip install

# Install PyTorch with CUDA 12.1 support (backward compatible with CUDA 12.4+)
# This must be installed before other dependencies to ensure proper CUDA support
pip install torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu124

# Install other Python dependencies
pip install -r requirements.txt

# Use mamba for faster dependency solving (drop-in replacement for conda)
# If mamba is not available, falls back to conda
if command -v mamba &> /dev/null; then
    mamba install habitat-sim -c conda-forge -c aihabitat -y
else
    # Use conda with solver options to speed up resolution
    conda install habitat-sim -c conda-forge -c aihabitat -y --solver=libmamba || \
    conda install habitat-sim -c conda-forge -c aihabitat -y
fi

cd ~
if [ ! -d "Hierarchical-Localization" ]; then
    git clone --recursive https://github.com/cvg/Hierarchical-Localization/
fi
cd Hierarchical-Localization/

# switch to a compatible version of hloc, see the commit: https://github.com/cvg/Hierarchical-Localization/commit/936040e8d67244cc6c8c9d1667701f3ce87bf075
git checkout 936040e8d67244cc6c8c9d1667701f3ce87bf075 

python -m pip install -e .
