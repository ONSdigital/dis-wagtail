#!/usr/bin/env bash
set -euo pipefail

TOTAL_SHARDS=${TOTAL_SHARDS:?TOTAL_SHARDS is required}
SHARD_INDEX=${SHARD_INDEX:?SHARD_INDEX is required} # 1-based: 1..TOTAL_SHARDS
SHUFFLE_SEED=${SHUFFLE_SEED:-}

# Validate numbers
[[ "$TOTAL_SHARDS" =~ ^[0-9]+$ ]] || {
    echo "TOTAL_SHARDS must be numeric" >&2
    exit 1
}
[[ "$SHARD_INDEX" =~ ^[0-9]+$ ]] || {
    echo "SHARD_INDEX must be numeric" >&2
    exit 1
}

# Convert to 0-based for modulo selection
shard_zero_based=$((SHARD_INDEX - 1))

seedfile=""
order_cmd=(sort)

if [[ -n "$SHUFFLE_SEED" ]]; then
    echo "Using seed '$SHUFFLE_SEED' for shuffling" >&2
    seedfile=$(mktemp)
    printf '%s' "$SHUFFLE_SEED" >"$seedfile"
    order_cmd=(shuf --random-source="$seedfile")
fi

find functional_tests/features -name '*.feature' |
    "${order_cmd[@]}" |
    awk "NR % $TOTAL_SHARDS == $shard_zero_based"

[[ -n "$seedfile" ]] && rm -f "$seedfile"
