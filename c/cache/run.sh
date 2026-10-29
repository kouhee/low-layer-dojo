#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"

if ! command -v valgrind >/dev/null 2>&1; then
    echo "Valgrind is required. Install it with: sudo apt install valgrind" >&2
    exit 1
fi

make cache-demo
./cache-demo benchmark

for mode in row column; do
    valgrind \
        --tool=cachegrind \
        --cache-sim=yes \
        --branch-sim=no \
        --instr-at-start=no \
        --I1=32768,8,64 \
        --D1=32768,8,64 \
        --LL=8388608,16,64 \
        --cachegrind-out-file="cachegrind.out.$mode" \
        ./cache-demo "$mode"
done

python3 report.py cachegrind.out.row cachegrind.out.column
