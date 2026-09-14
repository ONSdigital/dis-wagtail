import hashlib
import json
from typing import Any


def hash_chart_config(config: dict[str, Any]) -> str:
    """Hash a chart export config for detecting unchanged charts.

    Uses a canonical JSON serialisation (sorted keys, no whitespace) so that
    semantically identical configs always hash the same way.
    """
    serialized = json.dumps(config, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode()).hexdigest()


def numberfy(value: str) -> int | float | str:
    stripped = value.strip()
    if stripped.isdigit():
        return int(stripped)
    try:
        return float(stripped)
    except ValueError:
        pass
    return value
