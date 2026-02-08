#!/bin/bash
set -e

# Paths
SOURCE_DIR="/git/korev-evidence"
TARGET_DIR="/app"

# Copy repository files if run_ui.py is missing in /app (if the volume is mounted)
if [ ! -f "$TARGET_DIR/run_ui.py" ]; then
    echo "Copying files from $SOURCE_DIR to $TARGET_DIR..."
    cp -rn --no-preserve=ownership,mode "$SOURCE_DIR/." "$TARGET_DIR"
fi
