from django.db import close_old_connections
from django.test.runner import DiscoverRunner


class OldConnectionsCleanupDiscoveryRunner(DiscoverRunner):
    def teardown_databases(self, old_config, **kwargs):
        # close any lingering connections that prevent parallel tests from completing
        close_old_connections()
        super().teardown_databases(old_config, **kwargs)
