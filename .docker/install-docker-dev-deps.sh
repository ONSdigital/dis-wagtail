#!/usr/bin/env bash
# This is used in the `dev` target of the dockerfile to install necessary development dependencies

set -eux -o pipefail

apt --quiet --yes update
apt --quiet --yes install \
    git \
    gnupg \
    less \
    openssh-client \
    sudo
# Tidy up
apt --quiet --yes autoremove
rm -rf /var/lib/apt/lists/*
