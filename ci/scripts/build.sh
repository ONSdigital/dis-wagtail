#!/bin/sh
set -eu

# This script isn't necessary, it is to align with compiled code repos

# These directories will exist in the Concourse build environment
SRC_DIR="pull_request"
DST_DIR="build"

# Copy contents of pull_request into build (not the directory itself)
cp -pR "${SRC_DIR}/." "${DST_DIR}/"

# Ensure Concourse-specific Dockerfile exists in build
cp -p "${SRC_DIR}/Dockerfile" "${DST_DIR}/Dockerfile.concourse"
