FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Etc/UTC \
    CONDA_DIR=/opt/conda \
    PATH=/opt/conda/bin:$PATH

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    curl \
    wget \
    git \
    sudo \
    build-essential \
    cmake \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libx11-6 \
    libxext6 \
    libsm6 \
    libxrender1 \
    libssl-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Miniconda install
RUN wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh \
    && mkdir -p $CONDA_DIR \
    && bash /tmp/miniconda.sh -b -p $CONDA_DIR \
    && rm /tmp/miniconda.sh \
    && conda clean -afy

# Create environment
ARG PYTHON_VERSION=3.10
RUN conda update -n base -c defaults conda -y \
    && conda create -n vlmaps python=${PYTHON_VERSION} -y \
    && conda clean -afy

# Prepare workspace and caches
RUN mkdir -p /workspace /data /root/.cache/pip /root/.cache/huggingface
WORKDIR /workspace

# Install PyTorch with CUDA 12.1 first for better layer caching
SHELL ["/bin/bash", "-lc"]
RUN source activate vlmaps \
    && pip install --upgrade pip \
    && pip install --index-url https://download.pytorch.org/whl/cu121 torch torchvision torchaudio \
    && python -c "import torch; import torchvision; print('Torch:', torch.__version__, 'CUDA:', torch.version.cuda, 'Is CUDA:', torch.cuda.is_available())"

# Copy requirement files (only) for caching layer
COPY requirements.txt /tmp/requirements.txt
COPY requirements-dev.txt /tmp/requirements-dev.txt

# Install Python dependencies
RUN source activate vlmaps \
    && pip install -r /tmp/requirements.txt \
    && pip install -r /tmp/requirements-dev.txt \
    && conda clean -afy && pip cache purge || true

# Default working directory for the repo bind mount
WORKDIR /workspace/vlmaps

# Entrypoint to ensure conda env is active
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

# A sane default command for dev containers
CMD ["sleep", "infinity"]


