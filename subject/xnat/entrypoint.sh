#!/bin/bash
# Arguments are passed through unchanged:
#   <input_dir> <output_dir> <tools...> [--session <label>]   (EUCAIM jobman)
#   <tools...> --session <label>                              (XNAT; folders /input, /output)
# tools: snr si mi riciannoiselevel
set -e
echo "=== Starting IQA (subject level) ==="
python3 /app/iqa_subject.py "$@"
echo "=== Completed IQA ==="
