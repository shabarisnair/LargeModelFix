#!/usr/bin/env bash
# Generate + grade all three datasets for one model against one vLLM endpoint.
#   bash run_model.sh <model> <base_url> <tag> [extra generate.py args...]
# Each dataset runs in its own background chain (generate -> grade), so grading of a
# finished dataset overlaps generation of the others. Grading is CPU-only.
set -uo pipefail

MODEL="$1"; BASE_URL="$2"; TAG="$3"; shift 3
EXTRA=("$@")

ENV_PY=/home/ssn899/envs/largemodelfix/bin/python
ROOT=/hdd1/ssn899/LargeModelFix/results/r1distill_pass8
GEN="$ROOT/generations"; GRD="$ROOT/graded"; LOG="$ROOT/logs"
mkdir -p "$GEN" "$GRD" "$LOG"
cd "$(dirname "$0")"

pids=()
for d in gsm8k webinstruct livecodebench; do
  case "$d" in
    livecodebench) CONC=${CONC_LCB:-48} ;;   # ~30k tokens/response, the long pole
    *)             CONC=${CONC_OTHER:-32} ;;
  esac
  (
    out="$GEN/${TAG}__${d}.jsonl"
    "$ENV_PY" generate.py --model "$MODEL" --dataset "$d" --base-url "$BASE_URL" \
        --out "$out" --concurrency "$CONC" "${EXTRA[@]}" \
        >> "$LOG/${TAG}__${d}.gen.log" 2>&1 \
      && "$ENV_PY" grade.py --gen "$out" --outdir "$GRD" \
        >> "$LOG/${TAG}__${d}.grade.log" 2>&1
    echo "[$d] exit=$? -> $GRD"
  ) &
  pids+=($!)
done

fail=0
for p in "${pids[@]}"; do wait "$p" || fail=1; done
echo "run_model.sh done (tag=$TAG, fail=$fail)"
exit $fail
