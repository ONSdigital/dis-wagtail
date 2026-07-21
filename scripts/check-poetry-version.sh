#!/usr/bin/env bash
set -euo pipefail

pyproject_file="${PYPROJECT_FILE:-pyproject.toml}"
lock_file="${LOCK_FILE:-poetry.lock}"

required_version=$(grep -m1 '^requires-poetry' "${pyproject_file}" | sed -E 's/^requires-poetry[[:space:]]*=[[:space:]]*"([^"]+)"/\1/')

if [[ -z "${required_version}" ]]; then
    echo "Unable to find 'requires-poetry' in ${pyproject_file}." >&2
    exit 1
fi

lock_version=$(head -n1 "${lock_file}" | sed -E 's/.*Poetry ([0-9][^ ]*).*/\1/')

if [[ -z "${lock_version}" ]]; then
    echo "Unable to determine the Poetry version used to generate ${lock_file}." >&2
    exit 1
fi

if [[ "${required_version}" != "${lock_version}" ]]; then
    echo "Poetry version mismatch: ${pyproject_file} requires '${required_version}' but ${lock_file} was generated with '${lock_version}'." >&2
    exit 1
fi

echo "Poetry version '${required_version}' matches between ${pyproject_file} and ${lock_file}."
