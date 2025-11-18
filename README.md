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

- [Getting Started](#getting-started)
    - [Pre-requisites](#pre-requisites)
    - [Setup](#setup)
        - [Using Docker](#using-docker)
        - [Running locally with supporting services in Docker](#running-locally-with-supporting-services-in-docker)
- [Development](#development)
    - [Front-end tooling](#front-end-tooling)
    - [Adding Python packages](#adding-python-packages)
    - [Run Tests with Coverage](#run-tests-with-coverage)
    - [Functional Tests](#functional-tests)
    - [Linting and Formatting](#linting-and-formatting)
        - [Python](#python)
        - [Front-end](#front-end)
        - [pre-commit](#pre-commit)
        - [Megalinter](#megalinter-lintformat-non-python-files)
    - [Mailpit (Email Testing)](#mailpit-email-testing)
    - [Installing the Required LaTeX Packages for Local Development](#installing-the-required-latex-packages-for-local-development)
    - [Django Migrations](#django-migrations)
- [Contributing](#contributing)
- [License](#license)

For further developer documentation see [docs](docs/README.md)

## Getting Started

To get a local copy up and running, follow the steps below.

### Pre-requisites

Ensure you have the following installed:

1. **Python**: Version specified in `.python-version`. We recommend using [pyenv](https://github.com/pyenv/pyenv) for
   managing Python versions.
2. **[Poetry](https://python-poetry.org/)**: This is used to manage package dependencies and virtual
   environments.
3. **[Colima](https://github.com/ONSdigital/dp-compose/blob/main/setting-up-colima-locally.md)** for running the project
   in Docker containers.
4. **[PostgreSQL](https://www.postgresql.org/)** for the database. Provided as container via `docker-compose.yml` when
   using the Docker setup.
5. **[Node](https://nodejs.org/en)** and **[`nvm` (Node Version Manager)](https://github.com/nvm-sh/nvm)** for front-end
   tooling.
6. **[JQ](https://jqlang.github.io/jq/)** for the step in the build that installs the design system templates.
7. `texlive-latex-extra` and `texlive-fonts-recommended`: Required by `matplotlib` to render LaTeX equations. See [below](#installing-the-required-latex-packages-for-local-development) for instructions on how to install on macOS.
8. **Operation System**: Ubuntu/ MacOS.

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

    If this is your first time setting up the project, you’ll need to run migrations to set up the database schema, load the topics dev fixture, and create an
    administrative user.

    ```bash
    # ssh into the web container
    make docker-shell

    # Run database migrations
    make migrate

    # Load the topics dev fixture
    make load-topics

    # Create a superuser for accessing the admin interface
    make createsuperuser
    ```

3. **Compile translations**

In order to see pages in different languages, you'll need to compile the translations. This is done by running:

    ```bash
    make compilemessages
    ```

    This will create the necessary `.mo` files for the translations.

4. **Start Django Inside the Container**

    Once the containers are running, you need to manually start Django from within the web container.
    This allows for running both the Django server and any additional background services (e.g., schedulers).

    > ⚠️ WARNING
    > The `honcho` command will pick up your local mounted `.env` file when running via `docker-compose`.
    > Ensure that you comment out any variables in the `.env` file which might cause clashes in the container
    > context as they will take precedence when running `honcho start`.

    ```bash
    # Start both Django and the scheduler using Honcho
    honcho start

    # This is not needed if you used `honcho start`
    make runserver
    ```

You can then access the admin at `http://0.0.0.0:8000/admin/` or `http://localhost:8000/admin/`.

#### Running locally with supporting services in Docker

You can also run the main application locally with the supporting backend services such as the Postgres and Redis running in Docker.
This can be useful when you want to make changes that require the app to be restarted in order to be picked up.

The correct development configuration should be used by default when running from the shell. For IDEs you may need to add
`DJANGO_SETTINGS_MODULE=cms.settings.dev` to their runtime configuration (e.g [PyCharm configuration documentation](https://www.jetbrains.com/help/pycharm/run-debug-configuration.html#createExplicitly)).

In order to run it:

1. Pull the images of the supporting services.

    ```bash
    make compose-dev-pull
    ```

2. Start the supporting services in Docker.

    ```bash
    make compose-dev-up
    ```

3. Run the below command to apply the necessary pre-run steps, which include:

    - loading design system templates,
    - collecting the static files,
    - generating and applying database migrations,
    - loading the topics dev fixture
    - creating a superuser with:
        - username: `admin`
        - password: `changeme` # pragma: allowlist secret
    - setting the port the Wagtail site(s)

    ```bash
    make dev-init
    ```

4. Run the Django server locally via your IDE or with the following command:

    ```bash
    make runserver
    ```

#### Environment Configuration

By default, `make` targets will use the `cms.settings.dev` settings unless their commands explicitly use a different setting (via the `--settings` parameter or `DJANGO_SETTINGS_MODULE` environment variable)
is set in the environment. This default should work out of the box for local development.

To override settings in the environment, you can use a `.env` file. Note, however, that settings this file may also be picked up in the docker container, so
you may need to remove or rename the file, or comment out specific variables if you switch to running the app in the container.

> [!NOTE]
> When running the application locally in a virtual environment via Poetry the `.env` file will not be picked up automatically.
> For this to work you'll need to install the [poetry-plugin-dotenv](https://github.com/pivoshenko/poetry-plugin-dotenv).
> Note that this will not work if you have installed poetry via `brew`, it is recommended to install poetry via either `pipx` or the official installation
> script, see the [poetry installation docs](https://python-poetry.org/docs/#installation).

### External services

Some functionality in the application relies on external services, which the default configuration points to. An example is the Dataset API.
Access to these services may require additional setup, or a mocked version. Without it, the functionality will not work correctly.

## Development

Get started with development by running the following commands.
Before proceeding, make sure you have the development dependencies installed using the `make install-dev` command.

A Makefile is provided to simplify common development tasks. To view all available commands, run:

```bash
make
```

### Front-end tooling

While the end goal is to have all front-end elements in the
[Design System](https://service-manual.ons.gov.uk/design-system),
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

During tests, the `cms.settings.test` settings module is used. When running test without using `make test`, ensure this
settings module is used.

### Functional Tests

Our suite of functional browser driven tests uses [Behave](https://behave.readthedocs.io/en/latest/),
[Playwright](https://playwright.dev/python/docs/intro) and
[Django Live Server Test Cases](https://docs.djangoproject.com/en/stable/topics/testing/tools/#liveservertestcase) to
run BDD Cucumber feature tests against the app from a browser.

#### Installation

Install the Playwright dependencies (including its browser drivers) with:

```shell
make playwright-install
```

#### Run the Functional Tests

You can run the tests as an all-in-one command with:

```shell
make functional-tests
```

This will start and stop the docker compose services with the relevant tests.

To run the docker compose dependencies (database and redis) separately, e.g. if you want to run individual functional
tests yourself for development, start the docker compose dependencies with:

```shell
make functional-tests-up
```

This will start the dependent services in the background, allowing you to then run the tests separately.

Then once you are finished testing, stop the dependencies with:

```shell
make functional-tests-down
```

#### Showing the Tests Browser

By default, the tests will run in headless mode with no visible browser window.

To disable headless mode and show the browser, set `PLAYWRIGHT_HEADLESS=False` in the environment from which you are
running the tests. In this circumstance, you will probably also find it helpful to enable "slow mo" mode, which slows
down the automated browser interactions to make it possible to follow what the tests are doing. You can configure it
using the `PLAYWRIGHT_SLOW_MO` environment variable, passing it a value of milliseconds by which to slow each
interaction, e.g. `PLAYWRIGHT_SLOW_MO=1000` will cause each individual browser interaction from the tests to be delayed
by 1 second.

For example, you can run the tests with visible browser and each interaction slowed by a second by running:

```shell
PLAYWRIGHT_HEADLESS=False PLAYWRIGHT_SLOW_MO=1000 make functional-tests
```

#### Developing Functional Tests

Refer to the detailed [functional tests development docs](./functional_tests/README.md)

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

#### Django Migration Linter

[Django Migration Linter](https://github.com/3YOURMIND/django-migration-linter) for linting migrations files in the project.

To lint the django migration files:

```bash
make lint-migrations
```

##### Ignoring Migrations

If you need to bypass migration linting on certain files, add the migration name (the file name minus the `.py`) to the list of ignored migrations in the
`MIGRATION_LINTER_OPTIONS` setting in the [dev settings file](cms/settings/dev.py), with a comment explaining why the file is ignored.

#### Format

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
```

`pylint`, which is run as part of `pre-commit`, relies on the poetry packages all being installed. If you are running this on your local machine you need to install them if you have not done so previously. Poetry automatically creates a virtual environment when you do this, which the `pylint` command will make use of

```bash
# if you haven't run this locally previously
poetry install
```

`pylint` also relies on the [libpq](https://www.postgresql.org/docs/16/libpq.html) library being installed as a global package on your local machine. The installation steps below are for Macs.

```bash
brew install libpq
```

After the above command, follow the homebrew post-install instructions for PATH exports

```bash
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

### Mailpit (Email Testing)

Mailpit is a lightweight, local SMTP server and web interface that captures all outgoing email from our application without actually delivering it.
Rather than sending mail to real recipients, messages are stored in Mailpit’s inbox for easy inspection.

- **SMTP endpoint:** `localhost:1025`
- **Web UI:** [http://localhost:8025](http://localhost:8025)

Use Mailpit to:

- Preview email content, headers and attachments
- Verify templates and formatting before going to production
- Test email-related workflows

No additional configuration is needed here – our development settings already point at Mailpit’s SMTP port,
and every `send_mail` call will appear instantly in the UI.

> [!TIP]
> If you want to disable Mailpit and simply log emails to your console, switch to Django’s console backend:
>
> ```python
> EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
> ```

### Installing The Required LaTeX Packages For Local Development

In order to generate the equations in Wagtail using LaTeX strings via Matplotlib (Non-JS Equations), we will need to use `MacPorts` to install the following packages `texlive-latex-extra` and `texlive-fonts-recommended`.

As a prerequisite you will have to have [MacPorts](https://www.macports.org/install.php) installed.

```bash
sudo port install texlive-latex-extra texlive-fonts-recommended
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

### Translations

Translations are managed using .po files, which are compiled into .mo files for use in the application.
The .po files are located in the `cms/locale` directory.

If you add new text to the application, you will need to update the .po files to include the new text.
You can do this by running the following command:

```bash
make makemessages
```

This will scan the codebase for new text and update the .po files accordingly.

Once you have updated the .po files, you will need to compile them into .mo files for use in the application.

You can do this by running the following command:

```bash
make compilemessages
```

This will compile the .po files into .mo files, which are used by Django to display the translated text.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

See [LICENSE](LICENSE) for details.
