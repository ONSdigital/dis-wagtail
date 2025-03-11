#!/usr/bin/env bash
# Note: This file is loaded on all environments, even production.

if [ -n "$DEVCONTAINER" ]; then
    alias honcho="honcho -f .docker/Procfile"
fi
