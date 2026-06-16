"""Distributes functional test feature files across CI shards using greedy
bin-packing, with total line count as a proxy for test duration.

Each shard receives an approximately equal share of lines, so that parallel
CI jobs finish in roughly the same time.  The assigned feature file paths for
the current shard are written to ``features.txt``, one path per line.

Environment Variables:

    TOTAL_SHARDS
        The total number of parallel shards (must be a positive integer).
    SHARD_INDEX
        The 1-based index of the current shard (must satisfy
        ``1 <= SHARD_INDEX <= TOTAL_SHARDS``).
    SHUFFLE_SEED (optional)
        When set, the feature files are shuffled with this value as the random
        seed before bin-packing.  This prevents heavy files from always being
        co-located in the same shard across runs.  When omitted, files are sorted
        by ascending line count before packing, which is the most deterministic
        approach.
"""

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


def parse_env() -> tuple[int, int, str]:
    """Validate and return (total_shards, shard_index, shuffle_seed)."""
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
    if not 1 <= shard_index <= total_shards:
        sys.exit("SHARD_INDEX must be between 1 and TOTAL_SHARDS (inclusive)")

    return total_shards, shard_index, shuffle_seed


def load_sized_features(features_dir: Path, shuffle_seed: str) -> list[tuple[int, Path]]:
    """Return (line_count, path) pairs ordered ready for bin-packing."""
    files = sorted(features_dir.glob("*.feature"))  # sorted for determinism

    if not files:
        sys.exit(f"No .feature files found in {features_dir}")

    sized = [(count_lines(f), f) for f in files]

    if shuffle_seed:
        print(f"Using seed '{shuffle_seed}' for shuffling", file=sys.stderr)
        rng = random.Random(shuffle_seed)  # noqa
        rng.shuffle(sized)
    else:
        # Sort ascending so greedy packing works effectively without a seed.
        sized.sort(key=lambda x: x[0])

    return sized


def pack_shards(sized: list[tuple[int, Path]], total_shards: int) -> tuple[list[int], list[list[Path]]]:
    """Greedily assign files to shards; return (totals, assignments)."""
    totals: list[int] = [0] * total_shards
    assignments: list[list[Path]] = [[] for _ in range(total_shards)]

    for line_count, path in sized:
        min_shard = min(range(total_shards), key=lambda i: totals[i])
        totals[min_shard] += line_count
        assignments[min_shard].append(path)

    return totals, assignments


def print_shard_debug(totals: list[int], assignments: list[list[Path]], shard_zero: int) -> None:
    """Emit per-shard summary to stderr."""
    for i, (total, paths) in enumerate(zip(totals, assignments, strict=False)):
        marker = " <-- this shard" if i == shard_zero else ""
        print(
            f"Shard {i + 1}: {len(paths)} file(s), {total} lines{marker}",
            file=sys.stderr,
        )


def main() -> None:
    total_shards, shard_index, shuffle_seed = parse_env()
    shard_zero = shard_index - 1  # convert to 0-based

    sized = load_sized_features(Path("functional_tests/features"), shuffle_seed)
    totals, assignments = pack_shards(sized, total_shards)

    print_shard_debug(totals, assignments, shard_zero)

    output = Path("features.txt")
    output.write_text(
        "\n".join(str(p) for p in assignments[shard_zero]) + "\n",
        encoding="utf-8",
    )
    print(f"Written {len(assignments[shard_zero])} feature(s) to {output}", file=sys.stderr)


if __name__ == "__main__":
    main()
