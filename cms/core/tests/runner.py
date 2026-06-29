from django.db import close_old_connections
from django.test.runner import DiscoverRunner

from cms.post_publish_actions.executor import executor_stop_and_wait


class OldConnectionsCleanupDiscoveryRunner(DiscoverRunner):
    def teardown_databases(self, old_config, **kwargs):
        # Stop background threadpool to close any open connections.
        executor_stop_and_wait(progress=True)

        # close any lingering connections that prevent parallel tests from completing
        close_old_connections()
        super().teardown_databases(old_config, **kwargs)
