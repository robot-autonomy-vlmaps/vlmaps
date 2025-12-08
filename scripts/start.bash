#!/bin/bash

# Script to start/attach to vlmaps dev container using docker-compose
# Usage: ./scripts/start.bash [MP3D_DATA_DIR]
# Example: ./scripts/start.bash /path/to/data
# Or: VLMAPS_MP3D_DATA_DIR=/path/to/data ./scripts/start.bash

# Detect docker-compose command (supports both 'docker-compose' and 'docker compose')
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    echo "Error: docker-compose not found. Please install docker-compose."
    exit 1
fi

# Determine Matterport3D data directory
# Priority: 1) Command line argument, 2) VLMAPS_MP3D_DATA_DIR env var, 3) Warn and exit
if [ -n "$1" ]; then
    # Command line argument takes precedence
    export VLMAPS_MP3D_DATA_DIR="$1"
    echo "Using Matterport3D data directory (from argument): $VLMAPS_MP3D_DATA_DIR"
elif [ -n "$VLMAPS_MP3D_DATA_DIR" ]; then
    # Use environment variable if set
    echo "Using Matterport3D data directory (from VLMAPS_MP3D_DATA_DIR): $VLMAPS_MP3D_DATA_DIR"
else
    # Neither set - warn and exit
    echo "Error: Matterport3D data directory not specified." >&2
    echo "" >&2
    echo "Please set VLMAPS_MP3D_DATA_DIR environment variable or provide it as an argument:" >&2
    echo "  export VLMAPS_MP3D_DATA_DIR=/path/to/data" >&2
    echo "  ./scripts/start.bash" >&2
    echo "Or:" >&2
    echo "  ./scripts/start.bash /path/to/data" >&2
    exit 1
fi

# Check if container is running
if $DOCKER_COMPOSE ps 2>/dev/null | grep -q "vlmaps-dev.*Up"; then
    echo "Container is already running. Attaching..."
    $DOCKER_COMPOSE exec -e TERM=${TERM:-xterm-256color} vlmaps /bin/bash -c "source /opt/conda/etc/profile.d/conda.sh && conda activate vlmaps && exec /bin/bash"
else
    echo "Starting container with docker-compose..."
    $DOCKER_COMPOSE up -d
    echo "Attaching to container..."
    $DOCKER_COMPOSE exec -e TERM=${TERM:-xterm-256color} vlmaps /bin/bash -c "source /opt/conda/etc/profile.d/conda.sh && conda activate vlmaps && exec /bin/bash"
fi
