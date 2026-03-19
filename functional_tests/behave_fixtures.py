import time

import django
import psycopg
from behave import fixture
from behave.runner import Context
from django.conf import settings
from django.db import close_old_connections
from django.test.runner import DiscoverRunner
from django.test.testcases import LiveServerTestCase
from dslr.config import settings as dslr_settings
from dslr.operations import create_snapshot, delete_snapshot, find_snapshot, restore_snapshot

# Adapted from https://behave.readthedocs.io/en/stable/usecase_django.html#manual-integration


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
    # Initialize DSLR and take a snapshot of the clean, post migration test database
    initialize_dslr()
    context.clean_snapshot_name = "clean_snapshot"
    create_snapshot(context.clean_snapshot_name)

    # Yield to resume the tests execution
    yield  # Everything after this point is run after the entire test run

    context.test_runner.teardown_databases(context.old_db_config)
    context.test_runner.teardown_test_environment()
    delete_snapshot(find_snapshot(context.clean_snapshot_name))


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

    # Ensure the test case matches our multi DB configuration
    context.test_case_class.databases = frozenset({"default", "read_replica"})

    # The LiveServerTestCase setup will start a test server for our app, allowing us to test against a live app
    context.test_case_class.setUpClass()

    # This is the URL of the live server started by the test case
    # give it a shorter name since we'll need to access it in many places
    context.base_url = context.test_case_class.live_server_url

    # # Update the site entries' hostname and port
    # note: importing inline as the top-level imports happen before Django is initialised
    from wagtail.models import Site  # pylint: disable=import-outside-toplevel

    en_site = Site.objects.get(is_default_site=True)
    en_site.hostname = context.test_case_class.host
    en_site.port = context.test_case_class.server_thread.port
    en_site.save(update_fields=["hostname", "port"])

    cy_site = Site.objects.get(is_default_site=False)
    cy_site.hostname = f"cy.{context.test_case_class.host}"
    cy_site.port = context.test_case_class.server_thread.port
    cy_site.save(update_fields=["hostname", "port"])

    context.test_case = context.test_case_class()
    context.test_case.setUp()

    # Yield to resume the current scenario execution
    yield  # Everything after this point is run after the current scenario finishes

    # Prevent any remaining database connections from blocking further teardown
    close_old_connections()

    context.test_case.tearDown()

    # Try to restore the snapshot, which will reset the database to a clean state
    try:
        restore_snapshot(find_snapshot(context.clean_snapshot_name))
    except psycopg.OperationalError:
        # Try to close connections again, in case the restore fails due to open connections
        close_old_connections()
        # Wait in case there are some race conditions with the database connections
        time.sleep(1)
        # Retry the restore, if it fails again, the exception will be raised
        restore_snapshot(find_snapshot(context.clean_snapshot_name))

    context.test_case_class.tearDownClass()
    del context.test_case_class
    del context.test_case


def initialize_dslr() -> None:
    """Initialize DSLR to point to the Django default database."""
    db_config = settings.DATABASES["default"]
    db_conn_str = (
        f"postgresql://{db_config['USER']}:{db_config['PASSWORD']}"
        f"@{db_config['HOST']}:{db_config['PORT']}/{db_config['NAME']}"
    )
    dslr_settings.initialize(url=db_conn_str, debug=False)
