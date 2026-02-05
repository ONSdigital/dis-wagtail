# syntax=docker/dockerfile:1.10
# check=error=true

# NB: The above comments are special directives to Docker that enable us to use
# more up-to-date Dockerfile syntax and will cause the build to fail if any
# Docker build checks fail:
#  https://docs.docker.com/reference/build-checks/
#
# We've set it so that failing checks will cause `docker build .` to fail, but
# when that happens the error message isn't very helpful. To get more
# information, run `docker build --check .` instead.

# Build stage hierarchy:
#
#         ┌────────┐   ┌──────────────┐
#         │  base  │   │  frontend-*  │
#         └────────┘   └──────────────┘
#          /      \     /
#   ┌───────┐    ┌───────┐
#   │  dev  │    │  web  │
#   └───────┘    └───────┘
#

##############
# base stage #
##############

# This stage is the base for the web and dev stages. It contains the version of
# Python we want to use and any OS-level dependencies that we need in all
# environments. It also sets up the always-activated virtual environment and
# installs Poetry.

FROM python:3.14-slim AS base

WORKDIR /app

# Install the correct version of the Postgres client
# library (Debian's bundled version is normally too old)
ARG POSTGRES_VERSION=16

# Install common OS-level dependencies
# TODO: when moving to ONS infrastructure, replace RUN with:
# RUN --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
#     --mount=type=cache,target=/var/cache/apt,sharing=locked \
#     <<EOF
#     commands
# EOF
RUN apt --quiet --yes update \
    && apt --quiet --yes install --no-install-recommends \
        build-essential \
        curl \
        libpq-dev \
        git \
        jq \
        unzip \
        gettext \
        cm-super \
        postgresql-common \
        texlive-latex-extra \
    # Install the Postgres repo
    && /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh -y \
    # Install the Postgres client (matching production version)
    && apt --quiet --yes install --no-install-recommends postgresql-client-${POSTGRES_VERSION} \
    && apt --quiet --yes autoremove \
    && rm -rf /var/lib/apt/lists/*


# Create an unprivileged user and virtual environment for the app
ARG UID=1000
ARG GID=1000
ARG USERNAME=cms
ARG VIRTUAL_ENV=/venv
# TODO: when moving to ONS infrastructure, replace the RUN command with
# RUN <<OEF
#     # Create the unprivileged user and group. If you have issues with file
#     # ownership, you may need to adjust the UID and GID build args to match your
#     # local user.
#    groupadd --gid $GID $USERNAME
#    useradd --gid $GID --uid $UID --create-home $USERNAME
#    python -m venv --upgrade-deps $VIRTUAL_ENV
# EOF
RUN groupadd --gid $GID $USERNAME \
    && useradd --gid $GID --uid $UID --create-home $USERNAME \
    && python -m venv --upgrade-deps $VIRTUAL_ENV \
    && chown -R $UID:$GID /app $VIRTUAL_ENV

# Install Poetry in its own virtual environment
ARG POETRY_VERSION=2.2.1
ARG POETRY_HOME=/opt/poetry
# TODO: when moving to ONS infrastructure, replace RUN with
# RUN --mount=type=cache,target=/root/.cache/pip <<EOF
#     python -m venv --upgrade-deps $POETRY_HOME
#     $POETRY_HOME/bin/pip install poetry==$POETRY_VERSION
# EOF
RUN python -m venv --upgrade-deps $POETRY_HOME \
    && $POETRY_HOME/bin/pip install poetry==$POETRY_VERSION

# Set common environment variables
ENV \
    # Make sure the project code is always importable
    PYTHONPATH=/app \
    # Don't buffer Python output so that we don't lose logs in the event of a crash
    PYTHONUNBUFFERED=1 \
    # Let things know that a virtual environment is being used
    VIRTUAL_ENV=$VIRTUAL_ENV \
    # Make sure the virtual environment's bin directory and Poetry are on the PATH
    PATH=$VIRTUAL_ENV/bin:$POETRY_HOME/bin:$PATH

# Install .bashrc for dj shortcuts
COPY --chown=$UID:$GID ./.docker/bashrc.sh ./.docker/bashrc.sh

RUN ln -sTfv /app/.docker/bashrc.sh /home/$USERNAME/.bashrc

# Switch to the unprivileged user
USER $USERNAME

# Install the app's production dependencies. That prevents us
# needing to reinstall all the dependencies every time the app code changes.
COPY pyproject.toml poetry.lock ./
# TODO: when moving to ONS infrastructure, replace RUN with
# RUN --mount=type=cache,target=/home/$USERNAME/.cache/,uid=$UID,gid=$GID \
#     <<EOF
#     # Install the production dependencies
#     poetry install --no-root --without dev
# EOF
RUN poetry install --no-root --without dev


###################
# frontend stages #
###################

FROM node:20-slim AS frontend-deps

# This stage is used to install the front-end build dependencies. It's separate
# from the frontend-build stage so that we can initialise the node_modules
# volume in the dev container from here without needing to run the production
# build.

WORKDIR /build/

# Make any build & post-install scripts that respect this variable behave as if
# we were in a CI environment (e.g. for logging verbosity purposes)
ENV CI=true

# Install front-end dependencies
COPY package.json package-lock.json ./
# TODO: when moving to ONS infrastructure, replace RUN with
# RUN --mount=type=cache,target=/root/.npm \
#     npm ci --omit=optional --no-audit --progress=false
RUN npm ci --omit=optional --no-audit --progress=false


FROM frontend-deps AS frontend-build

# This stage is used to compile the front-end assets. The web stage copies the
# compiled assets bundles from here, so it doesn't need to have the front-end
# build dependencies installed.

# Compile static files
COPY .eslintignore .eslintrc.js .stylelintrc.js tsconfig.json webpack.config.js ./
COPY ./cms/static_src/ ./cms/static_src/
RUN npm run build:prod


#############
# dev stage #
#############

# This stage is used in the development environment, either via `fab sh` etc. or
# as the dev container in VS Code or PyCharm. It extends the base stage by
# adding additional OS-level dependencies to allow things like using git and
# psql. It also adds sudo and gives the unprivileged user passwordless sudo
# access to make things like experimenting with different OS dependencies easier
# without needing to rebuild the image or connect to the container as root.
#
# This stage does not include the application code at build time! Including the
# code would result in this image needing to be rebuilt every time the code
# changes at all which is unnecessary because we always bind mount the code at
# /app/ anyway.

FROM base AS dev

# Switch to the root user and Install extra OS-level dependencies for
# development, including Node.js
USER root
# TODO: when moving to ONS infrastructure, replace RUN with
# RUN --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
#     --mount=type=cache,target=/var/cache/apt,sharing=locked \
#     <<EOF

ARG GIT_COMMIT=""
ARG BUILD_TIME=""

ENV GIT_COMMIT=${GIT_COMMIT} BUILD_TIME=${BUILD_TIME}

# Set default shell with pipefail option
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN <<EOF
    apt --quiet --yes update
    apt --quiet --yes install \
        git \
        gnupg \
        less \
        openssh-client \
        sudo
    # Download and import the Nodesource GPG key
    mkdir -p /etc/apt/keyrings
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg
    # Create NodeSource repository
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" > /etc/apt/sources.list.d/nodesource.list
    # Update lists again and install Node.js
    apt --quiet --yes update
    apt --quiet --yes install nodejs
    # Tidy up
    apt --quiet --yes autoremove
    rm -rf /var/lib/apt/lists/*
EOF

# Give the unprivileged user passwordless sudo access
ARG USERNAME
RUN echo "$USERNAME ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Make less the default pager for things like psql results and git logs
ENV PAGER=less

# Flag that this is the dev container
ENV DEVCONTAINER=1

# Switch back to the unprivileged user
USER $USERNAME

# Copy in the node_modules directory from the frontend-deps stage to initialise
# the volume that gets mounted here
ARG UID=1000
ARG GID=1000
COPY --chown=$UID:$GID --from=frontend-deps --link /build/node_modules ./node_modules

# Install the dev dependencies (they're omitted in the base stage)
# TODO: when moving to ONS infrastructure, replace RUN with
# RUN --mount=type=cache,target=/home/$USERNAME/.cache/,uid=$UID,gid=$GID \
 #    poetry install
RUN poetry install

# Just do nothing forever - exec commands elsewhere
CMD ["tail", "-f", "/dev/null"]


#############
# web stage #
#############

# This is the stage that actually gets run in staging and production on Heroku.
# It extends the base stage by installing production Python dependencies and
# copying in the compiled front-end assets. It runs the WSGI server, gunicorn,
# in its CMD.

FROM base AS web

ARG GIT_COMMIT=""
ARG BUILD_TIME=""

# Set production environment variables
ENV \
    # Django settings module
    DJANGO_SETTINGS_MODULE=cms.settings.production \
    # Default port and number of workers for gunicorn to spawn
    PORT=8000 \
    WEB_CONCURRENCY=2 \
    # Commit SHA from building the project
    GIT_COMMIT=${GIT_COMMIT} \
    # Time the container was built
    BUILD_TIME=${BUILD_TIME}

# Copy in built static files and the application code. Run collectstatic so
# whitenoise can serve static files for us.
# TODO: when moving to ONS infrastructure, replace with:
# ARG UID
ARG UID=1000
# TODO: when moving to ONS infrastructure, replace with:
# ARG GID
ARG GID=1000

ARG USERNAME=cms

# Explicitly set the runtime user
USER $USERNAME

COPY --chown=$UID:$GID . .

# Get the Design System templates
RUN make load-design-system-templates

COPY --chown=$UID:$GID --from=frontend-build --link /build/cms/static_compiled ./cms/static_compiled
RUN django-admin collectstatic --noinput --clear && django-admin compilemessages

# Run Gunicorn using the config in gunicorn.conf.py (the default location for
# the config file). To change gunicorn settings without needing to make code
# changes and rebuild this image, set the GUNICORN_CMD_ARGS environment variable.
CMD ["gunicorn"]
