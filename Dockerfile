# Base image with NVIDIA CUDA with OPENGL support
FROM nvidia/cudagl:11.3.0-devel-ubuntu20.04

# Add NVIDIA GPG keys and repositories
RUN apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/3bf863cc.pub && \
    apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/7fa2af80.pub && \
    echo "deb https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64 /" > /etc/apt/sources.list.d/cuda.list && \
    echo "deb https://developer.download.nvidia.com/compute/machine-learning/repos/ubuntu2004/x86_64 /" > /etc/apt/sources.list.d/nvidia-ml.list

ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    git-lfs \
    curl \
    vim \
    ca-certificates \
    libjpeg-dev \
    libpng-dev \
    libglfw3-dev \
    libglm-dev \
    libx11-dev \
    libomp-dev \
    libegl1-mesa-dev \
    libgl1-mesa-glx \
    pkg-config \
    wget \
    zip \
    libxi-dev \
    libxcursor-dev \
    libxinerama-dev \
    libxrandr-dev \
    x11-apps \
    x11-xserver-utils \
    unzip && \
    rm -rf /var/lib/apt/lists/*

# Install Miniconda
RUN curl -L -o ~/miniconda.sh https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh && \
    chmod +x ~/miniconda.sh && \
    ~/miniconda.sh -b -p /opt/conda && \
    rm ~/miniconda.sh && \
    /opt/conda/bin/conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main && \
    /opt/conda/bin/conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r && \
    /opt/conda/bin/conda install numpy pyyaml scipy ipython mkl mkl-include -y && \
    /opt/conda/bin/conda install mamba -n base -c conda-forge -y && \
    /opt/conda/bin/conda clean -ya

# Add conda to PATH
ENV PATH=/opt/conda/bin:$PATH

# Install CMake
RUN wget https://github.com/Kitware/CMake/releases/download/v3.14.0/cmake-3.14.0-Linux-x86_64.sh && \
    mkdir /opt/cmake && \
    sh ./cmake-3.14.0-Linux-x86_64.sh --prefix=/opt/cmake --skip-license && \
    ln -s /opt/cmake/bin/cmake /usr/local/bin/cmake && \
    rm cmake-3.14.0-Linux-x86_64.sh

# Conda environment for vlmaps
RUN conda create -n vlmaps python=3.8 -y

# Configure conda for better dependency resolution
# Set conda-forge as default channel and use libmamba solver
RUN conda config --add channels conda-forge && \
    conda config --set channel_priority flexible

# Copy requirements.txt and install.bash for dependency installation
# These are copied during build (before volume mount at runtime)
COPY requirements.txt /tmp/requirements.txt
COPY install.bash /tmp/install.bash
RUN chmod +x /tmp/install.bash

# Install all dependencies (separated for easier debugging and better caching)
# This mirrors install.bash but uses direct conda paths (conda activate doesn't work in non-interactive RUN)
# IMPORTANT: Install habitat-sim FIRST via conda/mamba to avoid dependency conflicts with pip packages

# Step 1: Install habitat-sim first (before pip packages to avoid conflicts)
# Mamba is much faster than conda for dependency resolution and handles conflicts better
# Try mamba first, fall back to conda with libmamba solver, then regular conda
RUN /bin/bash -c "source /opt/conda/etc/profile.d/conda.sh && \
    /opt/conda/bin/mamba install -n vlmaps habitat-sim -c conda-forge -c aihabitat -y || \
    (/opt/conda/bin/conda install -n vlmaps habitat-sim -c conda-forge -c aihabitat -y --solver=libmamba || \
    /opt/conda/bin/conda install -n vlmaps habitat-sim -c conda-forge -c aihabitat -y) && \
    conda clean -ya"

# Step 2: Upgrade pip to compatible version and verify
RUN /opt/conda/envs/vlmaps/bin/python -m pip install --upgrade 'pip<24.1' && \
    /opt/conda/envs/vlmaps/bin/pip --version && \
    conda clean -ya

# Step 3: Install Python packages from requirements.txt
# Clean pip cache after installation to save space
RUN /opt/conda/envs/vlmaps/bin/pip install --no-cache-dir -r /tmp/requirements.txt && \
    /opt/conda/envs/vlmaps/bin/pip cache purge && \
    conda clean -ya

# Step 4: Clone Hierarchical-Localization
RUN cd ~ && \
    git clone --recursive https://github.com/cvg/Hierarchical-Localization/ && \
    cd Hierarchical-Localization && \
    git checkout 936040e8d67244cc6c8c9d1667701f3ce87bf075

# Step 5: Install Hierarchical-Localization
RUN cd ~/Hierarchical-Localization && \
    /opt/conda/envs/vlmaps/bin/python -m pip install --no-cache-dir -e . && \
    /opt/conda/envs/vlmaps/bin/pip cache purge

# Step 6: Clean up conda cache
RUN conda clean -ya

# Activate the vlmaps conda environment on container startup
RUN echo "source /opt/conda/etc/profile.d/conda.sh" >> ~/.bashrc && \
    echo 'export PYTHONPATH="${PYTHONPATH}:/vlmaps/"' >> ~/.bashrc && \
    echo "conda activate vlmaps" >> ~/.bashrc

# Set the working directory (will be overridden by volume mount)
WORKDIR /vlmaps
