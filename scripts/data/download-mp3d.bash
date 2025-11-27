#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ZIP_PATH="$PROJECT_ROOT/data/mp3d_habitat.zip"
TARGET_DIR="$PROJECT_ROOT/data/mp3d"
TEMP_V1_DIR="$PROJECT_ROOT/data/v1"

log() {
    printf '[download-mp3d] %s\n' "$1"
}

if [ ! -f "$PROJECT_ROOT/download_mp.py" ]; then
    echo "Error: download_mp.py not found in $PROJECT_ROOT." >&2
    echo "Place the Matterport-provided downloader in the project root." >&2
    exit 1
fi

mkdir -p "$PROJECT_ROOT/data"

download_zip() {
    if [ -f "$ZIP_PATH" ]; then
        log "Found existing mp3d_habitat.zip; skipping download."
        return
    fi

    log "Downloading Habitat task bundle (mp3d_habitat.zip). This is ~15GB."
    python download_mp.py -o "$PROJECT_ROOT/data" --task_data habitat

    local legacy_zip="$TEMP_V1_DIR/tasks/mp3d_habitat.zip"
    if [ -f "$legacy_zip" ]; then
        mv "$legacy_zip" "$ZIP_PATH"
        rm -rf "$TEMP_V1_DIR"
    fi

    if [ ! -f "$ZIP_PATH" ]; then
        echo "Download finished but $ZIP_PATH not found." >&2
        exit 1
    fi
}

extract_zip() {
    rm -rf "$TARGET_DIR"
    log "Extracting into $TARGET_DIR"
    unzip -oq "$ZIP_PATH" -d "$PROJECT_ROOT/data"

    if [ ! -d "$TARGET_DIR" ]; then
        echo "Extraction failed: expected $TARGET_DIR." >&2
        exit 1
    fi
}

download_zip
extract_zip

log "Done. Scenes extracted under $TARGET_DIR and archive stored at $ZIP_PATH."
