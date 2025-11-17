# Base image with NVIDIA CUDA 12.4 on Ubuntu 22.04 (OpenGL libs installed below)
ARG CUDA_IMAGE_TAG=12.4.1-devel-ubuntu22.04
FROM nvidia/cuda:${CUDA_IMAGE_TAG}

# Metadata labels for better image management
LABEL maintainer="robot-autonomy-vlmaps"
LABEL description="VLMaps Docker image with CUDA 12.4, Ubuntu 22.04, and all dependencies"
LABEL org.opencontainers.image.source="https://github.com/robot-autonomy-vlmaps/vlmaps"

# Build arguments for versioning (can be overridden)
ARG PYTHON_VERSION=3.10
ARG CMAKE_VERSION=3.14.0
ARG HLOC_COMMIT=936040e8d67244cc6c8c9d1667701f3ce87bf075

# Environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    PATH=/opt/conda/bin:$PATH \
    CONDA_AUTO_UPDATE_CONDA=false \
    PYTHONUNBUFFERED=1 \
    TERM=xterm-256color

# Install system dependencies in a single layer
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
    libgl1-mesa-dev \
    libgl1-mesa-glx \
    libglu1-mesa-dev \
    libxext6 \
    libdrm-dev \
    libxdamage-dev \
    libxcb1 \
    pkg-config \
    wget \
    zip \
    libxi-dev \
    libxcursor-dev \
    libxinerama-dev \
    libxrandr-dev \
    mesa-utils \
    x11-apps \
    x11-xserver-utils \
    unzip && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Install Miniconda and configure in a single layer
RUN curl -L -o /tmp/miniconda.sh https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh && \
    chmod +x /tmp/miniconda.sh && \
    /tmp/miniconda.sh -b -p /opt/conda && \
    rm /tmp/miniconda.sh && \
    /opt/conda/bin/conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main && \
    /opt/conda/bin/conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r && \
    /opt/conda/bin/conda install -y numpy pyyaml scipy ipython mkl mkl-include && \
    /opt/conda/bin/conda install -n base -c conda-forge -y mamba && \
    /opt/conda/bin/conda config --add channels conda-forge && \
    /opt/conda/bin/conda config --set channel_priority flexible && \
    /opt/conda/bin/conda clean -afy

# Install CMake
RUN wget -q https://github.com/Kitware/CMake/releases/download/v${CMAKE_VERSION}/cmake-${CMAKE_VERSION}-Linux-x86_64.sh -O /tmp/cmake.sh && \
    mkdir -p /opt/cmake && \
    sh /tmp/cmake.sh --prefix=/opt/cmake --skip-license && \
    ln -sf /opt/cmake/bin/cmake /usr/local/bin/cmake && \
    rm /tmp/cmake.sh

# Create conda environment and configure
RUN conda create -n vlmaps python=${PYTHON_VERSION} -y && \
    conda clean -afy

# Copy dependency files early for better layer caching
COPY requirements.txt /tmp/requirements.txt

# Install habitat-sim first (before pip packages to avoid conflicts)
# Use mamba for faster dependency resolution with fallback to conda
RUN /bin/bash -c "source /opt/conda/etc/profile.d/conda.sh && \
    /opt/conda/bin/mamba install -n vlmaps habitat-sim -c conda-forge -c aihabitat -y || \
    (/opt/conda/bin/conda install -n vlmaps habitat-sim -c conda-forge -c aihabitat -y --solver=libmamba || \
    /opt/conda/bin/conda install -n vlmaps habitat-sim -c conda-forge -c aihabitat -y) && \
    conda clean -afy"

# Upgrade pip and install PyTorch with CUDA 12.4 wheels
RUN /opt/conda/envs/vlmaps/bin/python -m pip install --no-cache-dir --upgrade pip && \
    /opt/conda/envs/vlmaps/bin/pip install --no-cache-dir torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu124 && \
    /opt/conda/envs/vlmaps/bin/pip install --no-cache-dir -r /tmp/requirements.txt && \
    /opt/conda/envs/vlmaps/bin/pip cache purge && \
    conda clean -afy

# Clone and install Hierarchical-Localization
RUN git clone --recursive https://github.com/cvg/Hierarchical-Localization.git ~/Hierarchical-Localization && \
    cd ~/Hierarchical-Localization && \
    git checkout ${HLOC_COMMIT} && \
    /opt/conda/envs/vlmaps/bin/pip install --no-cache-dir -e . && \
    /opt/conda/envs/vlmaps/bin/pip cache purge

# Configure shell environment for conda activation and colors
RUN echo "source /opt/conda/etc/profile.d/conda.sh" >> ~/.bashrc && \
    echo 'export PYTHONPATH="${PYTHONPATH}:/vlmaps/"' >> ~/.bashrc && \
    echo "conda activate vlmaps" >> ~/.bashrc && \
    echo 'export TERM=xterm-256color' >> ~/.bashrc && \
    echo 'alias ls="ls --color=auto"' >> ~/.bashrc && \
    echo 'alias grep="grep --color=auto"' >> ~/.bashrc && \
    echo 'alias fgrep="fgrep --color=auto"' >> ~/.bashrc && \
    echo 'alias egrep="egrep --color=auto"' >> ~/.bashrc && \
    echo 'export PS1="\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ "' >> ~/.bashrc

# Final cleanup
RUN conda clean -afy && \
    rm -rf /tmp/* /var/tmp/* /root/.cache

# Set working directory
WORKDIR /vlmaps

# Default command (can be overridden)
CMD ["/bin/bash"]
