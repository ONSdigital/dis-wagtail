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
# ensure TOTAL_SHARDS is > 0 to avoid division-by-zero
if [ "$TOTAL_SHARDS" -le 0 ]; then
    echo "TOTAL_SHARDS must be greater than 0" >&2
    exit 1
fi

[[ "$SHARD_INDEX" =~ ^[0-9]+$ ]] || {
    echo "SHARD_INDEX must be numeric" >&2
    exit 1
}
# ensure SHARD_INDEX is within 1..TOTAL_SHARDS
if [ "$SHARD_INDEX" -lt 1 ] || [ "$SHARD_INDEX" -gt "$TOTAL_SHARDS" ]; then
    echo "SHARD_INDEX must be between 1 and TOTAL_SHARDS (inclusive)" >&2
    exit 1
fi

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
