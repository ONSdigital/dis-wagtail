# Functional Tests

<!-- TOC -->

- [Functional Tests](#functional-tests)
    - [Structure](#structure)
    - [Dependencies](#dependencies)
        - [App Instance For Test Development](#app-instance-for-test-development)
        - [Clearing and Initialising the Functional Test Development Database](#clearing-and-initialising-the-functional-test-development-database)
            - [Using DSLR Snapshots for Development](#using-dslr-snapshots-for-development)
    - [Running the Tests](#running-the-tests)
        - [Playwright Options](#playwright-options)
    - [Developing Tests](#developing-tests)
        - [Useful Documentation](#useful-documentation)
    - [Viewing Failure Traces](#viewing-failure-traces)
        - [Viewing the Failure Trace from GitHub Actions](#viewing-the-failure-trace-from-github-actions)
    - [Test Data Setup](#test-data-setup)
    - [Test Code Standards and Style Guide](#test-code-standards-and-style-guide)
        - [Context Use](#context-use)
            - [Only step functions and environment hooks should interact with the context attributes](#only-step-functions-and-environment-hooks-should-interact-with-the-context-attributes)
        - [Sharing Code Between Steps](#sharing-code-between-steps)
        - [Step wording](#step-wording)
        - [Assertions](#assertions)
        - [Step parameter types](#step-parameter-types)
    - [How the Tests Work](#how-the-tests-work)
        - [Django Test Runner and Test Case](#django-test-runner-and-test-case)
        - [Database Snapshot and Restore](#database-snapshot-and-restore)
        - [Playwright](#playwright)
    - [Why Aren't We Using Existing Django Testing Modules?](#why-arent-we-using-existing-django-testing-modules)
        - [Pytest-BDD](#pytest-bdd)
        - [Behave-Django](#behave-django)

<!-- TOC -->

## Structure

Feature files live in the [features](./features) directory.

The steps implementations live in the [steps](./steps) directory, and it is recommended to group them into files based
on the domain they interact with. For example, certain page editor interactions are common to different features, the
steps for these can be made generic and kept in [page_editor.py](./steps/page_editor.py), rather than being duplicated
per feature.

## Dependencies

See the repo [README section](../README.md#functional-tests) for the basic setup guide for dependencies.

These tests require the backing services for the app to be running, as they run a live server instance of the app. We
accomplish this with docker compose, specifying the required backing services in the functional
tests [docker-compose.yml](./docker-compose.yml). These services are intentionally exposed on different ports to the
main local development dependencies, to avoid a conflict and allow them to run simultaneously.

You can start the dependencies in the background with:

```shell
make functional-tests-up
```

and stop them with:

```shell
make functional-tests-down
```

### App Instance For Test Development

Since the tests use a clean database state for every scenario, it will be easier to create tests on a similarly fresh,
empty database. However, it could quickly become inconvenient to have to tear down your main local environment every
time you want to replicate this state. To get around this, we can use this separate test instance, found at
`http://localhost:18000/`.

To start this test development app instance in docker along with the dependencies, run:

```shell
make functional-tests-dev-up
```

Then to stop it when you are finished, run:

```shell
make functional-tests-down
```

Which will also stop and remove the functional tests development app along with the dependencies, if it is running.

### Clearing and Initialising the Functional Test Development Database

To replicate the clean test database environment, you may want to completely clean your database.

You can use the django admin `reset_db` to completely clear the database, then re-run migrations to re-initialise the
tables and seeded data. Ensure you include the `DJANGO_SETTINGS_MODULE` environment variable, to avoid accidentally
wiping your normal local development environment.

```shell
poetry run python manage.py reset_db --settings=cms.settings.functional_test
poetry run python manage.py locked_migrate --settings=cms.settings.functional_test
```

Then for logging into the CMS, create a superuser with

```shell
DJANGO_SETTINGS_MODULE=cms.settings.functional_test make createsuperuser
```

#### Using DSLR Snapshots for Development

Resetting and migrating the DB will always work, but it is slow to run. A faster solution is
using [DSLR snapshots](https://pypi.org/project/dslr/). Note however, that these snapshots may break if the database
structure has changed, at which point you will need to reset and migrate again, then create a new, good snapshot.

Create a DSLR snapshot of the functional tests dev database with:

```shell
poetry run dslr --url postgresql://ons:ons@localhost:15432/ons snapshot <SNAPSHOT_NAME>  # pragma: allowlist secret
```

Then restore it with

```shell
poetry run dslr --url postgresql://ons:ons@localhost:15432/ons restore <SNAPSHOT_NAME>  # pragma: allowlist secret
```

## Running the Tests

See the [main README functional tests section](/README.md#run-the-functional-tests) for the basic commands for running
the tests.

### Playwright Options

Some Playwright configuration options can be passed in through environment variables

| Variable              | Description                                                                                                                                                                    | Default                          |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------- |
| PLAYWRIGHT_HEADLESS   | Toggle headless browser mode, set to "False" to show the browser window                                                                                                        | `True`                           |
| PLAYWRIGHT_SLOW_MO    | Sets the Playwright slow mo mode in milliseconds                                                                                                                               | `0`                              |
| PLAYWRIGHT_BROWSER    | Set the browser for playwright to use, must be one of `chromium`, `firefox`, or `webkit`.<br/> NOTE: Currently only chromium is supported and tests may fail in other browsers | `chromium`                       |
| PLAYWRIGHT_TRACE      | Toggle Playwright trace recording                                                                                                                                              | `True`                           |
| PLAYWRIGHT_TRACES_DIR | Sets the location to write Playwright trace files if `PLAYWRIGHT_TRACE` is enabled.<br/>The Default location `<project_root>/tmp_traces` is git ignored for convenience.       | `<working_directory>/tmp_traces` |

## Developing Tests

Watch [this video guide](https://www.loom.com/share/95e2b897ab2f4882adfe06cd2c90dada?sid=5042c0be-d726-4842-be84-153993e3db36) on creating functional tests. It
covers the basics of adding features, scenarios and steps and some Playwright tooling.

### Useful Documentation

Some links to particularly useful parts of documentation

- [Playwright Locators](https://playwright.dev/python/docs/locators): Locating and selecting page elements in Playwright
- [Playwright Assertions](https://playwright.dev/python/docs/test-assertions): Making assertions using Playwright
- [Playwright Codegen](https://playwright.dev/python/docs/codegen-intro): The Playwright code generator tool
- [Behave Command Line Arguments](https://behave.readthedocs.io/en/stable/behave#command-line-arguments): Options running the tests from the command line
- [Behave API Reference](https://behave.readthedocs.io/en/stable/api): Reference documentation for the Behave framework API

## Viewing Failure Traces

The tests record traces of all their actions, allowing you to follow through tests that previously ran and debug issues
in remote environments.

Our GitHub Action is configured to save traces of any failed scenario and upload them.

### Viewing the Failure Trace from GitHub Actions

1. Navigate to the failed Action functional test run, expand the "Upload Failure Traces" job step and click the download
   link to download the zip file of all failed scenario traces.
1. Unzip the downloaded file on the command line with

    ```shell
    unzip <path_to_file>
    ```

    (note that un-archiving using MacOS finder may not work as it recursively unzips the files inside, where we need the
    files inside to remain zipped)

1. This should leave you with a zip file for each failed scenario
1. Open the traces zip files one at a time using the [Playwright Trace Viewer](https://playwright.dev/docs/trace-viewer)

You should then be able to step through the failed tests and get a better idea of the state and cause of the failure.

## Test Data Setup

Some tests may require objects to be set up in the database, such as a user or set of pages that the feature relies
upon. For this, we can use [Factory Boy](https://factoryboy.readthedocs.io/en/stable/orms.html#django) to seed data
directly into the database. These factories should be shared with the rest of the tests and kept in the `tests` modules
alongside the code for consistency. If the functional tests need different defaults or behaviour from the factories,
then they can make use of [factory traits](https://factoryboy.readthedocs.io/en/stable/reference.html#traits).

## Test Code Standards and Style Guide

### Context Use

We make use of the [Behave Context](https://behave.readthedocs.io/en/stable/tutorial#context) object to store data
that is needed across multiple steps of a scenario.

To prevent the context from becoming cluttered and confusing to use, we define some rules for how we interact with it:

#### Only step functions and environment hooks should interact with the context attributes

Other none step or hook functions shouldn't be passed the entire context and should certainly not modify it. Instead,
pass in explicit variables from the context and return new ones as required. Try to make all none step functions
pure/deterministic.

This is to avoid the context use becoming obscured and hard to follow, when context variable are only set in top level
step functions then it is easy to follow where the variables for any particular scenario are set, simply by walking
through the steps. Passing the entire context object down to lower level functions effectively obscures their true
signatures, making the use and setting of context variables much harder to follow.

For example:

> [!TIP]
>
> **Do this:**
>
> ```python
> @step('a thing happens')
> def step_to_do_a_thing(context: Context):
>     context.a_new_context_var = helper_function(context.my_scenario_data)
>     ...
>
> def helper_function(my_scenario_data):
>     ...
>     return new_data
> ```

> [!CAUTION]
>
> **Not this:**
>
> ```python
> @step('a thing happens')
> def step_to_do_a_thing(context: Context):
>     helper_function_which_overwrites_context(context)
>     ...
>
> def helper_function_which_overwrites_context(context: Context) -> None:
>     ...
>     context.a_new_context_var = new_data
> ```

### Sharing Code Between Steps

Step files should not import code from other step files, where code can be shared between steps they should either be in
the same file, or the shared code should be factored out into the [step_helpers](step_helpers) module.

This is to avoid potential circular imports and make it clear which code is specific to certain steps, and which is
reusable across any steps.

Note that it is also perfectly valid to annotate the same step function with multiple different step wordings, for example to have multiple different wordings
of the step to make better grammatical sense in different scenarios.

### Step wording

Steps should be written in full and concise sentences, avoiding unnecessary abbreviations and shorthand. They should be
as understandable and as non-technical as possible.

### Assertions

Assertions should use the [Playwright assertions](https://playwright.dev/docs/test-assertions) wherever possible. This
has built in retry and timeout logic where applicable, to allow grace periods for content to load on the page, so will
be more robust than attempting to retrieve data from the page and make plain python assertions.

### Step parameter types

Where we need [step parameters](https://behave.readthedocs.io/en/stable/tutorial#step-parameters) to include more
complex data than single strings or the other basic types supported by the default parser, we
use [custom registered types](https://behave.readthedocs.io/en/stable/api#behave.register_type). These are
registered in the [environment.py](environment.py) so they are available to all steps.

## How the Tests Work

### Django Test Runner and Test Case

Due to [issues with the Django `TransactionTestCase`](#why-arent-we-using-existing-django-testing-modules) which prevent
us using the built-in database teardown/setup in between scenarios, we have implemented our own database snapshot and
restore pattern between tests. We still make use of the Django test case, specifically the
[`LiveServerTestCase`](https://docs.djangoproject.com/en/stable/topics/testing/tools/#django.test.LiveServerTestCase) to perform the initial database setup
and run a live server on a random port for the tests.

### Database Snapshot and Restore

We are using [DSLR](https://pypi.org/project/dslr/) for fast database snapshots and restores.

After we have used the Django test runner to set up the test database and initialise it by running migrations, we take a
DSLR snapshot of this clean, initial state. In the test case fixture, post test, we then restore the clean snapshot,
ensuring each test gets a clean, migrated database, isolated from other tests.

This setup is done in behave fixtures, kept in [behave_fixtures.py](behave_fixtures.py). These fixtures are the
registered in the behave hooks in the [environment.py](environment.py)

### Playwright

To give the scenario steps access to a playwright page, we set up a Playwright instance along with a browser and
browser context in the `before_all` hook, so that it is started once at the beginning of the run. In the
`before_scenario` hook, we then create a Playwright page object to be used by the scenario, passed to through the behave
context. This page is closed in the `after_scenario` hook, to ensure each scenario has its own separate page object.

If the `PLAYWRIGHT_TRACE` environment variable is enabled, we also start trace recording at the beginning of the run,
and start a new trace "chunk" for each scenario, so that traces of individual failed scenarios can be saved to files.

## Why Aren't We Using Existing Django Testing Modules?

At first glance it may appear our custom fixtures and database restore mechanism should be unnecessary, as there are
multiple choices for modules out there which claim to do what we need. We tried these solutions first and ruled them out
because of various incompatibilities with our app or testing requirements.

### Pytest-BDD

This is built on Pytest, and we decided to move our unit and integration testing away from Pytest because it has
compatibility issues with our multi-DB configuration, so this would have suffered the same issue.

Live server testing is accomplished with a fixture, which under the hood uses a Django `LiveServerTestCase`. This
inherits from the
[`TransactionTestCase`](https://docs.djangoproject.com/en/stable/topics/testing/tools/#django.test.TransactionTestCase), which causes us serious compatibility
issues, as it uses an isolated test database and flushes all data in between tests. We have migrations which seed critical data rows, so a flush operation
breaks the app. The `serialised_rollback`option for the test case may present a solution in the future, but this depends on restoring any migration seeded data
with fixtures, which currently runs into an issue with Wagtails Locale models.

We tried various workarounds such as using a fixture file to restore the data, but this runs into Wagtail issues, and
even if it worked it would be non-ideal as that fixture file would have to be kept up to date and recreated when any new
seeded data is added.

### Behave-Django

Behave-Django is a module which enables easier integration between the Behave BDD framework and a Django app. It uses
the Django `StaticLiveServerTestCase` and Django test runner to wrap the Behave test runs. This means we run into the
exact same data flushing issue as we did with Pytest-BDD.

Also, the `StaticLiveServerTestCase` is incompatible with Whitenoise, which we use to serve static content, so we would
have to override the test case. This was possible, but the setting was only exposed through command line arguments, so
it would make running the scenarios through an IDE with debugging features either imp
