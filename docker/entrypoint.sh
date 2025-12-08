#!/usr/bin/env bash
set -euo pipefail

# Initialize conda for bash shells
if [ -f "/opt/conda/etc/profile.d/conda.sh" ]; then
  source /opt/conda/etc/profile.d/conda.sh
fi

conda activate vlmaps || true
exec "$@"


