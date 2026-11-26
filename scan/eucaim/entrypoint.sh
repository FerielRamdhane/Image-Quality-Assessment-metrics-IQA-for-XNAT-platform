#!/bin/bash
# Arguments are passed through unchanged:
#   <input_dir> <output_dir> <tools...>    (EUCAIM jobman)
#   <tools...>                             (folders from INPUT_DIR / OUTPUT_DIR, default /input /output)
# tools: snr si mi riciannoiselevel
set -e
echo "=== Starting IQA (scan level) ==="
python3 /app/iqa_scan.py "$@"
echo "=== Completed IQA ==="
