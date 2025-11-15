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

# Install all dependencies using install.bash
# This ensures single source of truth - update install.bash, not Dockerfile
# Docker layer caching: each step is cached, so rebuilds are faster if only code changes
RUN /bin/bash -c "source /opt/conda/etc/profile.d/conda.sh && \
    conda activate vlmaps && \
    cd /tmp && \
    cp requirements.txt . && \
    bash install.bash && \
    conda clean -ya && \
    rm -rf ~/Hierarchical-Localization/.git"

# Activate the vlmaps conda environment on container startup
RUN echo "source /opt/conda/etc/profile.d/conda.sh" >> ~/.bashrc && \
    echo 'export PYTHONPATH="${PYTHONPATH}:/vlmaps/"' >> ~/.bashrc && \
    echo "conda activate vlmaps" >> ~/.bashrc

# Set the working directory (will be overridden by volume mount)
WORKDIR /vlmaps
