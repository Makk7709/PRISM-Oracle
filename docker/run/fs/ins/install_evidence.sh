#!/bin/bash
set -e

# Exit immediately if a command exits with a non-zero status.
# set -e

# branch from parameter
if [ -z "$1" ]; then
    echo "Error: Branch parameter is empty. Please provide a valid branch name."
    exit 1
fi
BRANCH="$1"

if [ "$BRANCH" = "local" ]; then
    # For local branch, use the files
    echo "Using local dev files in /git/korev-evidence"
else
    # For other branches, clone from GitHub
    echo "Cloning repository from branch $BRANCH..."
    git clone -b "$BRANCH" "https://github.com/korevai/korev-evidence" "/git/korev-evidence" || {
        echo "CRITICAL ERROR: Failed to clone repository. Branch: $BRANCH"
        exit 1
    }
fi

. "/ins/setup_venv.sh" "$@"

# moved to base image
# # Ensure the virtual environment and pip setup
# pip install --upgrade pip ipython requests
# # Install some packages in specific variants
# pip install torch --index-url https://download.pytorch.org/whl/cpu

# Install KOREV Evidence python packages
uv pip install -r /git/korev-evidence/requirements.txt
# override for packages that have unnecessarily strict dependencies
uv pip install -r /git/korev-evidence/requirements2.txt

# install playwright
bash /ins/install_playwright.sh "$@"

# Preload KOREV Evidence
python /git/korev-evidence/preload.py --dockerized=true
