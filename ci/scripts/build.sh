#!/bin/sh
set -eu

# Temporary: required because the Concourse pipeline expects Dockerfile.concourse.
# This exists to support repositories that still override the image registry
# via string replacement in the Dockerfile rather than using build arguments.
# Can be removed once all application Dockerfiles migrate to build args.

# These directories will exist in the Concourse build environment
SRC_DIR="pull_request"
DST_DIR="build"

# Copy contents of pull_request into build (not the directory itself)
cp -pR "${SRC_DIR}/." "${DST_DIR}/"

# Ensure Concourse-specific Dockerfile exists in build
cp -p "${SRC_DIR}/Dockerfile" "${DST_DIR}/Dockerfile.concourse"
