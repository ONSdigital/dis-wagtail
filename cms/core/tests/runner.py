from django.db import close_old_connections, connections
from django.test.runner import DiscoverRunner

from cms.post_publish_actions.executor import executor_stop_and_wait


class OldConnectionsCleanupDiscoveryRunner(DiscoverRunner):
    def setup_databases(self, **kwargs):
        config = super().setup_databases(**kwargs)

        # Running tests with the --parallel flag was failing due to attribute errors in the django parallel test
        # runner setup. This adds a quick monkey patch that allows tests to run.
        # Raised here, but will need to reopen or start a new ticket for followup
        # https://code.djangoproject.com/ticket/37077
        for alias in connections:
            if not hasattr(connections[alias], "_test_serialized_contents"):
                connections[alias]._test_serialized_contents = ""  # pylint: disable=W0212
        return config

    def teardown_databases(self, old_config, **kwargs):
        # Stop background threadpool to close any open connections.
        executor_stop_and_wait(progress=True)

        # close any lingering connections that prevent parallel tests from completing
        close_old_connections()
        super().teardown_databases(old_config, **kwargs)
