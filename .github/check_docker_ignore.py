#!/usr/bin/env python
"""A script to confirm that the project's `.dockerignore` and `.gitignore` are in sync."""

import difflib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[1]

GITIGNORE = PROJECT_ROOT / ".gitignore"
DOCKERIGNORE = PROJECT_ROOT / ".dockerignore"

MARKER = "# The below must be in sync with `.gitignore`."


def main() -> None:
    dockerignore_text = DOCKERIGNORE.read_text().splitlines()
    gitignore_text = GITIGNORE.read_text().splitlines()

    start_index = dockerignore_text.index(MARKER)

    diff = list(
        difflib.unified_diff(
            dockerignore_text[start_index + 1 :],
            gitignore_text[1:],
            fromfile=str(DOCKERIGNORE),
            tofile=str(GITIGNORE),
            lineterm="",
        )
    )

    if diff:
        print("\n".join(diff))
        sys.exit(1)
    else:
        print(f"{GITIGNORE} matches {DOCKERIGNORE}")


if __name__ == "__main__":
    main()
