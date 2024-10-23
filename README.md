# dis-wagtail

[![Build Status](https://github.com/ONSdigital/dis-wagtail/actions/workflows/ci.yml/badge.svg)](https://github.com/ONSdigital/dis-wagtail/actions/workflows/ci.yml)
[![Build Status](https://github.com/ONSdigital/dis-wagtail/actions/workflows/mega-linter.yml/badge.svg)](https://github.com/ONSdigital/dis-wagtail/actions/workflows/mega-linter.yml)
[![Build Status](https://github.com/ONSdigital/dis-wagtail/actions/workflows/codeql.yml/badge.svg)](https://github.com/ONSdigital/dis-wagtail/actions/workflows/codeql.yml)

[![Linting: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![poetry-managed](https://img.shields.io/badge/poetry-managed-blue)](https://python-poetry.org/)
[![License - MIT](https://img.shields.io/badge/licence%20-MIT-1ac403.svg)](https://github.com/ONSdigital/dis-wagtail/blob/main/LICENSE)

The Django Wagtail CMS for managing and publishing content for the Office for National Statistics (ONS)

---

## Table of Contents

[//]: # ':TODO: Enable link checking once https://github.com/tcort/markdown-link-check/issues/250 is resolved.'

<!-- markdown-link-check-disable -->

-   [Getting Started](#getting-started)
    -   [Pre-requisites](#pre-requisites)
    -   [Installation](#installation)
-   [Development](#development)
    -   [Run Tests with Coverage](#run-tests-with-coverage)
    -   [Linting and Formatting](#linting-and-formatting)
-   [Contributing](#contributing)
-   [License](#license)
<!-- markdown-link-check-enable -->

## Getting Started

To get a local copy up and running, follow these simple steps.

### Pre-requisites

Ensure you have the following installed:

1. **Python**: Version specified in `.python-version`. We recommend using [pyenv](https://github.com/pyenv/pyenv) for
   managing Python versions.
2. **[Poetry](https://python-poetry.org/)**: This is used to manage package dependencies and virtual
   environments.
3. **[Docker](https://docs.docker.com/engine/install/)**
4. **Operation System**: Ubuntu/MacOS

### Setup

1. Clone the repository

    ```bash
    git clone https://github.com/ONSdigital/dis-wagtail.git
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

3. Build the docker container

    ```bash
    make docker-build
    ```

4. Run the docker container

    ```bash
    make docker-start
    # ssh into the web container
    make docker-shell
    # in the web container
    $ djrun
    ```

### Using Docker

```bash
git clone https://github.com/ONSdigital/dis-wagtail
cd dis-wagtail
make docker-build
make docker-start
```

This will start the containers in the background, but not Django. To do this, connect to the web container with `make docker-shell` and run `honcho start` to start both
Django and the scheduler in the foreground, or just `djrun`.

Upon first starting the container, the static files may not exist, or may be out of date.
To resolve this, run `make load-design-system-templates`.

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

The unit tests are written using the [pytest](https://docs.pytest.org/en/stable/) framework. To run the tests and check
coverage, run:

```bash
make test
```

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

## Front-end

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
$ pre-commit install

# Optional, run all checks once for this, then the checks will run only on the changed files
$ pre-commit run --all-files
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

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

See [LICENSE](LICENSE) for details.
