# Base image with NVIDIA CUDA support
FROM nvidia/cudagl:10.1-devel-ubuntu18.04

# Add NVIDIA GPG keys and repositories
RUN apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu1804/x86_64/3bf863cc.pub && \
    apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu1804/x86_64/7fa2af80.pub && \
    echo "deb https://developer.download.nvidia.com/compute/cuda/repos/ubuntu1804/x86_64 /" > /etc/apt/sources.list.d/cuda.list && \
    echo "deb https://developer.download.nvidia.com/compute/machine-learning/repos/ubuntu1804/x86_64 /" > /etc/apt/sources.list.d/nvidia-ml.list

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

# Install Miniconda (using version compatible with Ubuntu 18.04 GLIBC 2.27)
RUN curl -L -o ~/miniconda.sh https://repo.anaconda.com/miniconda/Miniconda3-py38_4.9.2-Linux-x86_64.sh && \
    chmod +x ~/miniconda.sh && \
    ~/miniconda.sh -b -p /opt/conda && \
    rm ~/miniconda.sh && \
    /opt/conda/bin/conda install numpy pyyaml scipy ipython mkl mkl-include -y && \
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

# Copy requirements.txt and install.bash for dependency installation
# These are copied during build (before volume mount at runtime)
COPY requirements.txt /tmp/requirements.txt
COPY install.bash /tmp/install.bash
RUN chmod +x /tmp/install.bash

# Install all dependencies (separated for easier debugging and better caching)
# This mirrors install.bash but uses direct conda paths (conda activate doesn't work in non-interactive RUN)

# Step 1: Upgrade pip to compatible version and verify
RUN /opt/conda/envs/vlmaps/bin/python -m pip install --upgrade 'pip<24.1' && \
    /opt/conda/envs/vlmaps/bin/pip --version

# Step 2: Install Python packages from requirements.txt
# Using verbose output to see what's failing
RUN /opt/conda/envs/vlmaps/bin/pip install --verbose -r /tmp/requirements.txt || \
    (echo "Failed to install packages. Checking pip and requirements.txt..." && \
    /opt/conda/envs/vlmaps/bin/pip --version && \
    cat /tmp/requirements.txt && \
    exit 1)

# Step 3: Install habitat-sim (this is the slowest step, ~10-15 minutes)
RUN /bin/bash -c "source /opt/conda/etc/profile.d/conda.sh && \
    conda run -n vlmaps --no-capture-output conda install habitat-sim=0.2.2 -c conda-forge -c aihabitat -y"

# Step 4: Clone Hierarchical-Localization
RUN cd ~ && \
    git clone --recursive https://github.com/cvg/Hierarchical-Localization/ && \
    cd Hierarchical-Localization && \
    git checkout 936040e8d67244cc6c8c9d1667701f3ce87bf075

# Step 5: Install Hierarchical-Localization
RUN cd ~/Hierarchical-Localization && \
    /opt/conda/envs/vlmaps/bin/python -m pip install -e .

# Step 6: Clean up conda cache
RUN conda clean -ya

# Activate the vlmaps conda environment on container startup
RUN echo "source /opt/conda/etc/profile.d/conda.sh" >> ~/.bashrc && \
    echo 'export PYTHONPATH="${PYTHONPATH}:/vlmaps/"' >> ~/.bashrc && \
    echo "conda activate vlmaps" >> ~/.bashrc

# Set the working directory (will be overridden by volume mount)
WORKDIR /vlmaps
