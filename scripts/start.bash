#!/bin/bash

# Script to start/attach to vlmaps dev container using docker-compose
# Usage: ./scripts/start.bash

# Detect docker-compose command (supports both 'docker-compose' and 'docker compose')
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    echo "Error: docker-compose not found. Please install docker-compose."
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
