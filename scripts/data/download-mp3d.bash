#!/bin/bash

# Script to download Matterport3D data using download_mp.py
# Run from project root directory (works both locally and in Docker)
# Usage: ./scripts/data/download-mp3d.bash [SCENE_ID]
# Example: ./scripts/data/download-mp3d.bash 17DRP5sb8fy

set -e  # Exit on error

# Get project root from script location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

# Data directories (relative to project root)
DATA_DIR="$PROJECT_ROOT/data/mp3d"
VLMAPS_DATA_DIR="$PROJECT_ROOT/data/vlmaps"

# Check if download_mp.py exists
if [ ! -f "$PROJECT_ROOT/download_mp.py" ]; then
    echo "Error: download_mp.py not found in project root ($PROJECT_ROOT)" >&2
    echo "" >&2
    echo "Please copy the download_mp.py script provided by Matterport3D into the project root." >&2
    exit 1
fi

# Function to update config file
update_config_file() {
    CONFIG_FILE="$PROJECT_ROOT/config/data_paths/default.yaml"
    if [ ! -f "$CONFIG_FILE" ]; then
        echo "Warning: Config file not found at $CONFIG_FILE"
        echo "You may need to create it or update the path manually."
        return
    fi
    
    echo ""
    echo "Would you like to update config/data_paths/default.yaml to point to the data directory?"
    echo ""
    echo "Current config:"
    cat "$CONFIG_FILE"
    echo ""
    read -p "Update config file? (yes/no): " update_config
    
    if [[ "$update_config" =~ ^[Yy][Ee][Ss]$ ]]; then
        # Use relative paths in config (works both locally and in Docker)
        HABITAT_SCENE_DIR_CFG="data/mp3d/scans"
        VLMAPS_DATA_DIR_CFG="data/vlmaps"
        
        # Backup original config
        cp "$CONFIG_FILE" "${CONFIG_FILE}.bak"
        
        # Update config file
        sed -i "1s|.*|habitat_scene_dir: \"$HABITAT_SCENE_DIR_CFG\"|" "$CONFIG_FILE"
        sed -i "2s|.*|vlmaps_data_dir: \"$VLMAPS_DATA_DIR_CFG\"|" "$CONFIG_FILE"
        
        echo ""
        echo "Config file updated successfully!"
        echo "Backup saved to: ${CONFIG_FILE}.bak"
        echo ""
        echo "New config:"
        cat "$CONFIG_FILE"
    else
        echo "Config file not updated. You can update it manually later."
    fi
}

# Check if data directory exists and has content
OVERWRITE=false
SHOULD_DOWNLOAD=true
if [ -d "$DATA_DIR" ] && [ -n "$(ls -A "$DATA_DIR" 2>/dev/null)" ]; then
    echo "Warning: Data directory already exists and contains files: $DATA_DIR" >&2
    echo "" >&2
    echo "Options:" >&2
    echo "  1. Overwrite existing data (this will delete existing scans/ and tasks/ directories)" >&2
    echo "  2. Skip download and only update config" >&2
    echo "  3. Exit and manage data directory manually" >&2
    echo "" >&2
    read -p "Do you want to overwrite existing data? (yes/no/skip): " response
    if [[ "$response" =~ ^[Ss][Kk][Ii][Pp]$ ]]; then
        SHOULD_DOWNLOAD=false
        echo "Skipping download. Will ask about config update..."
    elif [[ ! "$response" =~ ^[Yy][Ee][Ss]$ ]]; then
        echo "Aborted. Data will remain in $DATA_DIR" >&2
        # Still ask about config before exiting
        update_config_file
        exit 1
    else
        OVERWRITE=true
        echo "Proceeding with overwrite..."
    fi
fi

# Download data if needed
if [ "$SHOULD_DOWNLOAD" = true ]; then
    # Create data directory if it doesn't exist
    mkdir -p "$DATA_DIR"
    
    # Clear existing scans and tasks directories if overwriting
    if [ "$OVERWRITE" = true ]; then
        echo "Clearing existing data directories..."
        rm -rf "$DATA_DIR/scans" "$DATA_DIR/tasks"
    fi
    
    # Get scene ID from argument or use default
    SCENE_ID="${1:-17DRP5sb8fy}"
    echo "Using scene ID: $SCENE_ID"
    
    echo "Downloading Matterport3D data to: $DATA_DIR"
    echo "This may take a while (approximately 50GB)..."
    echo ""
    
    # Download scans
    echo "Downloading scans for scene $SCENE_ID..."
    python download_mp.py -o "$DATA_DIR/scans" --id "$SCENE_ID" || {
        echo "Error: Failed to download scans" >&2
        exit 1
    }
    if [ -d "$DATA_DIR/scans/v1/scans/$SCENE_ID" ]; then
        cp -a "$DATA_DIR/scans/v1/scans/$SCENE_ID/." "$DATA_DIR/scans/" && \
        rm -rf "$DATA_DIR/scans/v1"
    fi
    
    # Download tasks
    echo "Downloading habitat tasks..."
    python download_mp.py -o "$DATA_DIR/tasks" --task habitat
    if [ -f "$DATA_DIR/tasks/v1/tasks/mp3d_habitat.zip" ]; then
        unzip -q "$DATA_DIR/tasks/v1/tasks/mp3d_habitat.zip" -d "$DATA_DIR/tasks" && \
        rm -rf "$DATA_DIR/tasks/v1"
    fi
    
    # Create vlmaps directory for future use
    mkdir -p "$VLMAPS_DATA_DIR"
    
    echo ""
    echo "Download complete!"
    echo "Matterport3D data is available at: $DATA_DIR"
    echo ""
    echo "Directory structure:"
    echo "  $DATA_DIR/scans/         - Matterport3D scene scans"
    echo "  $DATA_DIR/tasks/         - Habitat tasks"
    echo "  $VLMAPS_DATA_DIR/        - VLMaps dataset (will be populated by generate_dataset.py)"
else
    echo "Skipping download. Using existing data at: $DATA_DIR"
    # Ensure vlmaps directory exists even when skipping download
    mkdir -p "$VLMAPS_DATA_DIR"
fi

# Always ask to update config file (regardless of whether data was downloaded)
update_config_file
