# dis-wagtail

[![Build Status](https://github.com/ONSdigital/dis-wagtail/actions/workflows/ci.yml/badge.svg)](https://github.com/ONSdigital/dis-wagtail/actions/workflows/ci.yml)
[![Build Status](https://github.com/ONSdigital/dis-wagtail/actions/workflows/mega-linter.yml/badge.svg)](https://github.com/ONSdigital/dis-wagtail/actions/workflows/mega-linter.yml)
[![Build Status](https://github.com/ONSdigital/dis-wagtail/actions/workflows/codeql.yml/badge.svg)](https://github.com/ONSdigital/dis-wagtail/actions/workflows/codeql.yml)

[![Linting: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![poetry-managed](https://img.shields.io/badge/poetry-managed-blue)](https://python-poetry.org/)
[![License - MIT](https://img.shields.io/badge/licence%20-MIT-1ac403.svg)](https://github.com/ONSdigital/dis-wagtail/blob/main/LICENSE)

The Wagtail CMS for managing and publishing content for the Office for National Statistics (ONS)

---

## Table of Contents

[//]: # ':TODO: Enable link checking once https://github.com/tcort/markdown-link-check/issues/250 is resolved.'

<!-- markdown-link-check-disable -->

-   [Getting Started](#getting-started)
    -   [Pre-requisites](#pre-requisites)
    -   [Setup](#setup)
        -   [Using Docker](#using-docker)
        -   [Running locally with supporting services in Docker](#running-locally-with-supporting-services-in-docker)
-   [Development](#development)
    -   [Front-end tooling](#front-end-tooling)
    -   [Adding Python packages](#adding-python-packages)
    -   [Run Tests with Coverage](#run-tests-with-coverage)
    -   [Linting and Formatting](#linting-and-formatting)
        -   [Python](#python)
        -   [Front-end](#front-end)
        -   [pre-commit](#pre-commit)
        -   [Megalinter](#megalinter-lintformat-non-python-files)
    -   [Django Migrations](#django-migrations)
-   [Contributing](#contributing)
-   [License](#license)
<!-- markdown-link-check-enable -->

For further developer documentation see [docs](docs/index.md)

## Getting Started

To get a local copy up and running, follow the steps below.

### Pre-requisites

Ensure you have the following installed:

1. **Python**: Version specified in `.python-version`. We recommend using [pyenv](https://github.com/pyenv/pyenv) for
   managing Python versions.
2. **[Poetry](https://python-poetry.org/)**: This is used to manage package dependencies and virtual
   environments.
3. **[Colima](https://github.com/ONSdigital/dp-compose/blob/main/setting-up-colima-locally.md)** for running the project in Docker containers.
4. **[PostgreSQL](https://www.postgresql.org/)** for the database. Provided as container via `docker-compose.yml` when using the Docker setup.
5. **[Node](https://nodejs.org/en)** and **[`nvm` (Node Version Manager)](https://github.com/nvm-sh/nvm)** for front-end tooling.
6. **[JQ](https://jqlang.github.io/jq/)** for the step in the build that installs the design system templates
7. **Operation System**: Ubuntu/MacOS

### Setup

1. Clone the repository

    ```bash
    git clone git@github.com:ONSdigital/dis-wagtail.git
    ```

2. Install dependencies

    [Poetry](https://python-poetry.org/) is used to manage dependencies in this project. For more information, read
    the [Poetry documentation](https://python-poetry.org/).

    To install all dependencies, including development dependencies, run:

    ```bash
    make install-dev
    ```

    To install only production dependencies, run:

    ```bash
    make install
    ```

#### Using Docker

Follow these steps to set up and run the project using Docker.

1. **Build and Start the Containers**

    ```bash
    # pull the supporting containers
    make compose-pull

    # build the main application image
    make compose-build

    # start the containers
    make compose-up
    ```

2. **Migrations and Superuser Creation**

    If this is your first time setting up the project, you’ll need to run migrations to set up the database schema and create an administrative user.

    ```bash
    # ssh into the web container
    make docker-shell

    # Run database migrations
    make migrate

    # Create a superuser for accessing the admin interface
    make createsuperuser
    ```

3. **Start Django Inside the Container**

    Once the containers are running, you need to manually start Django from within the web container. This allows for running both the Django server and any additional background services (e.g., schedulers).

    ⚠️ WARNING  
    The `honcho` command will pick up your local mounted `.env` file when running via `docker-compose`. Ensure that you comment out any variables in the `.env` file which might cause clashes in the container context as they will take precedence when running `honcho start`.

    ```bash
    # Start both Django and the scheduler using Honcho
    honcho start

    # This is not needed if you used `honcho start`
    make runserver
    ```

You can then access the admin at `http://0.0.0.0:8000/admin/` or `http://localhost:8000/admin/`.

#### Running locally with supporting services in Docker

You can also run the main application locally with the supporting backend services such as the Postgres and Redis running in Docker. This can be useful when you want to make changes that require the app to be frequently restarted to be picked up.

In order to run it:

1. Pull the images of the supporting services.

```
make compose-dev-pull
```

2. Start the supporting services in Docker.

```
make compose-dev-up
```

3. Run the below command to run the necessary pre-run steps:

```
make dev-init
```

4. Run the Django server locally via your IDE or with the following command:

```
make runserver
```

You can specify the runtime configuration either in your IDE (for PyCharm see [here](https://www.jetbrains.com/help/pycharm/run-debug-configuration.html#createExplicitly)), or copy the `.development.env` and rename it to `.env` which will allow Django to pick up the config.
Note that once you create the `.env` file, and you'd like to switch back to running the application in a container with `make compose-up`, the `.env` file will be accessible inside the containers and it will be picked up by the `honcho` command. In order to avoid conflicts you should comment out the `DATABASE_URL` and `REDIS_URL` variables in the `.env` file.

> [!NOTE]
> When running the application in a virtual environment via Poetry the `.env` file will not be picked up automatically. For this to work you'll need to install the [poetry-plugin-dotenv](https://github.com/pivoshenko/poetry-plugin-dotenv). However if you installed Poetry with `brew` rather than `pip` that currently isn't going to work (see the [issue](https://github.com/pivoshenko/poetry-plugin-dotenv/issues/327)) and you'll need to install an older and seemingly no longer maintained [poetry-dotenv-plugin](https://github.com/mpeteuil/poetry-dotenv-plugin).

## Development

Get started with development by running the following commands.
Before proceeding, make sure you have the development dependencies installed using the `make install-dev` command.

A Makefile is provided to simplify common development tasks. To view all available commands, run:

```bash
make
```

### Front-end tooling

While the end goal is to have all front-end elements in the [Design System](https://service-manual.ons.gov.uk/design-system),
the new design introduces a number of components that we need to build and contributed to the DS. In order to aid
development and avoid being blocked by the DS, we will use modern front-end tooling for that.

Here are the common commands:

```bash
# Install front-end dependencies.
npm install
# Start the Webpack build in watch mode, without live-reload.
npm run start
# Start the Webpack server build on port 3000 only with live-reload.
npm run start:reload
# Do a one-off Webpack development build.
npm run build
# Do a one-off Webpack production build.
npm run build:prod
```

### Adding Python packages

Python packages can be installed using `poetry` in the web container:

```bash
make docker-shell
poetry add wagtailmedia
```

### Run Tests with Coverage

To run the tests and check coverage, run:

```bash
make test
```

During tests, the `cms.settings.test` settings module is used. When running test without using `make test`, ensure this settings module is used.

### Linting and Formatting

Various tools are used to lint and format the code in this project.

#### Python

The project uses [Ruff](https://github.com/astral-sh/ruff) and [pylint](https://pylint.pycqa.org/en/latest/index.html)
for linting and formatting of the Python code.

The tools are configured using the `pyproject.toml` file.

To lint the Python code, run:

```bash
make lint
```

To auto-format the Python code, and correct fixable linting issues, run:

```bash
make format
```

#### Front-end

```bash
# lint and format custom CSS/JS
npm run lint
# only CSS
npm run lint:css
# only JS
npm run lint:js
# check css, js, markdown and yaml formatting
npm run lint:format
# format
npm run format
```

#### pre-commit

Note that this project has configuration for [pre-commit](https://github.com/pre-commit/pre-commit). To set up locally:

```bash
# if you don't have it yet, globally
pip install pre-commit

# in the project directory, initialize pre-commit
pre-commit install

# Optional, run all checks once for this, then the checks will run only on the changed files
pre-commit run --all-files
```

The `detect-secrets` pre-commit hook requires a baseline secrets file to be included. If you need to, \
you can update this file, e.g. when adding dummy secrets for unit tests:

```bash
poetry run detect-secrets scan > .secrets.baseline
```

#### MegaLinter (Lint/Format non-python files)

[MegaLinter](https://github.com/oxsecurity/megalinter) is utilised to lint the non-python files in the project.
It offers a single interface to execute a suite of linters for multiple languages and formats, ensuring adherence to
best practices and maintaining consistency across the repository without the need to install each linter individually.

MegaLinter examines various file types and tools, including GitHub Actions, Shell scripts, Dockerfile, etc. It is
configured using the `.mega-linter.yml` file.

To run MegaLinter, ensure you have **Docker** installed on your system.

> Note: The initial run may take some time to download the Docker image. However, subsequent executions will be
> considerably faster due to Docker caching. :rocket:

To start the linter and automatically rectify fixable issues, run:

```bash
make megalint
```

### Django Migrations

Wagtail is built on [Django](https://djangoproject.com/) and changes to its models may require generating and
running schema migrations. For full details see the [Django documentation on migrations](https://docs.djangoproject.com/en/5.1/topics/migrations/)

Below are the commands you will most commonly use, note that these have to be run inside the container.

```bash
# Check if you need to generate any new migrations after changes to the model
make makemigrations-check

# Generate migrations
make makemigrations

# Apply migrations. Needed if new migrations have been generated (either by you, or via upstream code)
make migrate
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

See [LICENSE](LICENSE) for details.
