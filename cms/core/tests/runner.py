from django.db import close_old_connections, connections
from django.test.runner import DiscoverRunner


class OldConnectionsCleanupDiscoveryRunner(DiscoverRunner):
    def setup_databases(self, **kwargs):
        config = super().setup_databases(**kwargs)

        for alias in connections:
            if not hasattr(connections[alias], "_test_serialized_contents"):
                connections[alias]._test_serialized_contents = ""  # pylint: disable=W0212
        return config

    def teardown_databases(self, old_config, **kwargs):
        # close any lingering connections that prevent parallel tests from completing
        close_old_connections()
        super().teardown_databases(old_config, **kwargs)
