#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 3 ]]; then
  echo "Usage: $0 CONFIG [MODEL_PATH] [OUTPUT_DIR]" >&2
  exit 2
fi

config=$1
model_path=${2:-}
output=${3:-benchmark-results/reproduction}

args=(benchmark --suite microswe --config "$config" --output "$output")
if [[ -n "$model_path" ]]; then
  args+=(--model-path "$model_path")
fi

python -m mitecoder "${args[@]}"
