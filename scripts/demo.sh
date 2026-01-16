#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

export LLM_PROVIDER=mock
OUTPUT_DIR=${1:-output}
export ADVERSARIAL_BEAD_LEDGER="$OUTPUT_DIR/ledger.jsonl"

python3 -m adversarial_debate.cli run examples/mini-app/ --output "$OUTPUT_DIR"

latest_run=$(ls -dt "$OUTPUT_DIR"/run-* 2>/dev/null | head -n 1 || true)
if [ -n "$latest_run" ]; then
  echo "Latest run: $latest_run"
  echo "Artifacts:"
  ls -1 "$latest_run"
else
  echo "Run completed. Output dir: $OUTPUT_DIR"
fi
