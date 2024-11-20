import os
import subprocess
from pathlib import Path

import django
from behave import fixture
from behave.runner import Context
from django.conf import settings
from django.db import close_old_connections
from django.test.runner import DiscoverRunner
from django.test.testcases import LiveServerTestCase

# Adapted from https://behave.readthedocs.io/en/stable/usecase_django.html#manual-integration

# Allow the path to the postgres client tools we depend on to be configured from the environment,
# as they may not always be accessible by name
PG_DUMP = os.getenv("PG_DUMP", "/usr/local/bin/pg_dump")
PG_RESTORE = os.getenv("PG_RESTORE", "/usr/local/bin/pg_restore")


@fixture
def django_test_runner(context: Context) -> None:
    """A behave fixture to wrap the test run in a Django test runner.
    This sets up a test database (prefixed with `test_`) so the test runs are isolated.
    Saves a database dump to a file, to allow tests to reset the database to a clean, initial state.
    Designed to be registered as a 'before_all' fixture, so that the setup occurs once before the tests,
    and teardown follows after the entire run finishes.
    """
    # Set up Django, and it's test runner to give us a clean test database and initialised/set up Django resources
    django.setup()
    context.test_runner = DiscoverRunner()
    context.test_runner.setup_test_environment()
    context.old_db_config = context.test_runner.setup_databases()

    # At this point, the Django test runner has initialised the test database and run migrations
    # We dump the database out to a file, to allow us to later restore the database to this clean, initial state
    context.initial_pg_dump_file = dump_database_to_file()

    # Yield to resume the tests execution
    yield  # Everything after this point is run after the entire test run

    context.test_runner.teardown_databases(context.old_db_config)
    context.test_runner.teardown_test_environment()
    context.initial_pg_dump_file.unlink(missing_ok=True)  # Delete the dump file


@fixture
def django_test_case(context: Context) -> None:
    """A behave fixture to wrap a behave scenario in a Django test case.
    Restores the database to a clean state after the test using the clean dump file, to ensure the database is left in
    a clean state for subsequent tests.
    Designed to be registered as a 'before_scenario' fixture, so that each scenario is wrapped in a Django test case
    setup and teardown.
    """
    # Use the LiveServerTestCase instead of the StaticLiveServerTestCase as the static version conflicts with our
    # use of whitenoise for serving static content.
    context.test_case_class = LiveServerTestCase

    # The LiveServerTestCase setup will start a test server for our app, allowing us to test against a live app
    context.test_case_class.setUpClass()

    # This is the URL of the live server started by the test case
    # give it a shorter name since we'll need to access it in many places
    context.base_url = context.test_case_class.live_server_url

    context.test_case = context.test_case_class()
    context.test_case.setUp()

    # Yield to resume the current scenario execution
    yield  # Everything after this point is run after the current scenario finishes

    # Prevent any remaining database connections from blocking further teardown
    close_old_connections()

    context.test_case.tearDown()
    restore_database_dump(context.initial_pg_dump_file)
    context.test_case_class.tearDownClass()
    del context.test_case_class
    del context.test_case


def dump_database_to_file() -> Path:
    """Dump the Django default database out to a file.
    Returns the Path for the dumped file.
    """
    dump_file = Path("tmp_test_pg_dump.sql")

    db_config = settings.DATABASES["default"]

    # Use the pg_dump utility to dump the entire database out into the dump file
    with dump_file.open("w", encoding="utf-8") as write_file:
        subprocess.run(  # noqa: S603
            [
                PG_DUMP,
                "--format=custom",  # Custom format is required to use pg_restore,
                "-d",
                db_config["NAME"],
                "-h",
                db_config["HOST"],
                "-p",
                str(db_config["PORT"]),
                "-U",
                db_config["USER"],
            ],
            stdout=write_file,
            env={"PGPASSWORD": db_config["PASSWORD"]},  # The password cannot be passed on the command line
            check=True,
        )
    return dump_file


def restore_database_dump(dump_file: Path) -> None:
    """Do a clean restore on the default Django database from a dump file."""
    db_config = settings.DATABASES["default"]

    # Use the pg_restore utility to load the database dump file
    subprocess.run(  # noqa: S603
        [
            PG_RESTORE,
            "--format=custom",
            "--clean",  # Custom format is required to use pg_restore,
            "-d",
            db_config["NAME"],
            "-h",
            db_config["HOST"],
            "-p",
            str(db_config["PORT"]),
            "-U",
            db_config["USER"],
            dump_file.absolute(),
        ],
        env={"PGPASSWORD": db_config["PASSWORD"]},  # The password cannot be passed on the command line
        check=True,
    )
