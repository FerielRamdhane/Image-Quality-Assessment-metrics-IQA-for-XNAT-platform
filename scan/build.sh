#!/bin/bash
# Build the scan-level IQA images from the repository root.
#   bash build.sh xnat      XNAT image (needs the shared MATLAB Runtime base on this machine)
#   bash build.sh eucaim    self-contained EUCAIM image (no MATLAB needed)
set -euo pipefail
cd "$(dirname "$0")"
TARGET="${1:?Usage: bash build.sh xnat | eucaim}"
VERSION=$(grep -oP '^TOOL_VERSION = "\K[^"]+' src/iqa_common.py)
case "$TARGET" in
  xnat)
    MCR_BASE="${MCR_BASE:-mcr-riciannoiselevel:r2024b}"
    docker image inspect "$MCR_BASE" > /dev/null 2>&1 \
      || { echo "✗ Shared MATLAB Runtime base '$MCR_BASE' not found on this machine"; exit 1; }
    docker build -f xnat/Dockerfile --build-arg MCR_BASE="$MCR_BASE" -t "iqaxnat_scan:${VERSION}-xnat" . ;;
  eucaim)
    docker build -f eucaim/Dockerfile -t "iqaxnat_scan:${VERSION}" . ;;
  *) echo "Unknown target '$TARGET' (use: xnat | eucaim)"; exit 1 ;;
esac
echo "=== Done ==="
