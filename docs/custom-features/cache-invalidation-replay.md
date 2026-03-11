# Cache Invalidation Replay

In our [multiple deployment environments](./deployment-environments.md), each deployment has its own cache to prevent accidentally caching unpublished data. However, if a change in the CMS needs to purge a cache, the "External" environment isn't aware.

The `InvalidateReplayRedisCache` cache backend supports "replaying" cache invalidations to a second cache (configured as `invalidate_replay`). Whenever caches are purged, they're first removed from the default backend, and then additionally replayed to the `invalidate_replay` backend

The expected deployment is that the "Internal" environment is configured with the "External" environment's cache as its `invalidate_replay` address. The "External" environment configuration does not change.
