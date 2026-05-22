# pylint: skip-file

import os
import random
import sys
from pathlib import Path


def count_lines(path: Path) -> int:
    try:
        with path.open("rb") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def main() -> None:
    raw_total = os.environ.get("TOTAL_SHARDS", "")
    raw_index = os.environ.get("SHARD_INDEX", "")
    shuffle_seed = os.environ.get("SHUFFLE_SEED", "")

    if not raw_total:
        sys.exit("TOTAL_SHARDS is required")
    if not raw_index:
        sys.exit("SHARD_INDEX is required")

    if not raw_total.isdigit():
        sys.exit("TOTAL_SHARDS must be numeric")
    if not raw_index.isdigit():
        sys.exit("SHARD_INDEX must be numeric")

    total_shards = int(raw_total)
    shard_index = int(raw_index)  # 1-based

    if total_shards <= 0:
        sys.exit("TOTAL_SHARDS must be greater than 0")
    if not (1 <= shard_index <= total_shards):
        sys.exit("SHARD_INDEX must be between 1 and TOTAL_SHARDS (inclusive)")

    shard_zero = shard_index - 1  # convert to 0-based

    # --- Discover feature files ---
    features_dir = Path("functional_tests/features")
    files = sorted(features_dir.glob("*.feature"))  # sorted for determinism

    if not files:
        sys.exit(f"No .feature files found in {features_dir}")

    # --- Attach line counts ---
    sized = [(count_lines(f), f) for f in files]

    # --- Order before packing ---
    if shuffle_seed:
        print(f"Using seed '{shuffle_seed}' for shuffling", file=sys.stderr)
        rng = random.Random(shuffle_seed)  # noqa
        rng.shuffle(sized)
    # Sort ascending by line count so greedy packing works effectively;
    # when a seed is given the shuffle already breaks size-ordering deliberately
    # to avoid always co-locating heavy files — so only sort without a seed.
    else:
        sized.sort(key=lambda x: x[0])

    # --- Greedy bin-packing ---
    totals: list[int] = [0] * total_shards
    assignments: list[list[Path]] = [[] for _ in range(total_shards)]

    for line_count, path in sized:
        min_shard = min(range(total_shards), key=lambda i: totals[i])
        totals[min_shard] += line_count
        assignments[min_shard].append(path)

    # --- Emit debug info ---
    for i, (total, paths) in enumerate(zip(totals, assignments, strict=False)):
        marker = " <-- this shard" if i == shard_zero else ""
        print(
            f"Shard {i + 1}: {len(paths)} file(s), {total} lines{marker}",
            file=sys.stderr,
        )

    # --- Write output ---
    output = Path("features.txt")
    output.write_text(
        "\n".join(str(p) for p in assignments[shard_zero]) + "\n",
        encoding="utf-8",
    )
    print(f"Written {len(assignments[shard_zero])} feature(s) to {output}", file=sys.stderr)


if __name__ == "__main__":
    main()
