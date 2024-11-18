import os
import subprocess
from pathlib import Path

import django
from behave import fixture
from behave.runner import Context
from django.conf import settings
from django.test.runner import DiscoverRunner
from django.test.testcases import LiveServerTestCase

# Adapted from https://behave.readthedocs.io/en/stable/usecase_django.html#manual-integration

PG_DUMP = os.getenv("PG_DUMP", "/usr/local/bin/pg_dump")
PG_RESTORE = os.getenv("PG_RESTORE", "/usr/local/bin/pg_restore")


@fixture
def django_test_runner(context: Context) -> None:
    """A behave fixture to wrap a test run in a Django test runner.
    This sets up a test database (prefixed with `test_`) so the test runs are isolated.
    Intended to be registered as a before_all fixture to ensure an entire run is isolated.
    """
    django.setup()
    context.test_runner = DiscoverRunner()
    context.test_runner.setup_test_environment()
    context.old_db_config = context.test_runner.setup_databases()
    context.initial_pg_dump_file = dump_database_to_file()

    # Yield to resume the tests execution
    yield  # Everything after this point is run after the entire test run

    context.test_runner.teardown_databases(context.old_db_config)
    context.test_runner.teardown_test_environment()
    context.initial_pg_dump_file.unlink(missing_ok=True)


@fixture
def django_test_case(context: Context) -> None:
    """A behave fixture to wrap a test case in a Django test case.
    Intended to be registered as a before_scenario fixture, so that each scenario is wrapped in a test case setup and
    teardown.
    """
    context.test_case_class = LiveServerTestCase
    context.test_case_class.setUpClass()
    context.test_case = context.test_case_class()
    context.base_url = context.test_case_class.live_server_url
    context.test_case.setUp()

    # Yield to resume the current scenario execution
    yield  # Everything after this point is run after the current scenario finishes

    context.test_case.tearDown()
    restore_database_dump(context.initial_pg_dump_file)
    context.test_case_class.tearDownClass()
    del context.test_case_class


def dump_database_to_file() -> Path:
    """Dump the Django default database out to a file.
    Returns the Path for the dumped file.
    """
    dump_file = Path("tmp_test_pg_dump.sql")

    db_config = settings.DATABASES["default"]

    # Use the pg_dump utility to dump the entire database out into the dump file
    with dump_file.open("w", encoding="utf-8") as outfile:
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
            stdout=outfile,
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
