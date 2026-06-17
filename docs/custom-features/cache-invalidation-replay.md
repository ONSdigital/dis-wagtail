# Cache Invalidation Replay

In our [multiple deployment environments](./deployment-environments.md), each deployment has its own cache to prevent accidentally caching unpublished data. However, if a change in the CMS needs to purge a cache, the "External" environment isn't aware.

The `InvalidateReplayRedisCache` cache backend supports "replaying" cache invalidations to a second cache (configured as `invalidate_replay`). Whenever caches are purged, they are first applied to the `invalidate_replay` backend, and then to the `default`.

This ordering is intentional. The `invalidate_replay` cache represents the external-facing environment, so keeping it fresh is more critical. If an invalidation fails, it is safer for the internal cache to become stale than for external users to be served outdated content.

The `clear` operation is not replayed to allow separate entire cache purges.

The expected deployment is that the "Internal" environment is configured with the "External" environment's cache as its `invalidate_replay` address. The "External" environment configuration does not change.
