#!/bin/bash -eux

# Build the application
pushd pull_request
  mkdir -p build
  cp build/dis-wagtail Dockerfile ../build
popd
