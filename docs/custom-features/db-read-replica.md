# Database Read-Replica

Each deployed environment uses a primary-replica model for the database. Write queries are sent to the primary instance, whilst read queries are balanced between a number of replicas. Replica instances are read-only - any write queries sent to them will return an error. For this reason, database migrations are only run against the primary instance.

To ensure a consistent view of the database, the write instance is always used if there is an open transaction, even for reads.

Generally, a developer shouldn't need to worry about this configuration, or explicitly handle it - it is handled automatically by a database router (`cms.core.db_router.ReadReplicaRouter`).

> [!WARNING]
> For performance-critical areas, some of Django's built-in queries should be avoided: `get_or_create`, `update_or_create`. These methods result in queries which always use the primary database instance. Instead, it may be better to use multiple explicit queries (eg `.get` then `.create`) so that the optimal connection is used.
