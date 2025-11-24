# Database Read-Replica

Each deployed environment uses a primary-replica model for the database. Write queries are sent to the primary instance, whilst read queries are balanced
between a number of replicas. Replica instances are read-only - any write queries sent to them will return an error. For this reason, database migrations are
only run against the primary instance.

To ensure a consistent view of the database, the write instance is always used if there is an open transaction, even for reads.

Generally, a developer shouldn't need to worry about this configuration, or explicitly handle it - it is handled automatically by a database router (
`cms.core.db_router.ReadReplicaRouter`).

## Coding considerations when using read-replicas

### Replication Lag

> [!WARNING]
> There is a small delay between writes to the primary instance and when those writes are visible on the replicas.

This means that immediately attempting to read data from the replicas after writing it may return stale data, leading to race conditions and intermittent bugs
which can only present.

This can be avoided by ensuring that any read-after-write operations are performed on the primary write instance. There are a couple of different ways to
achieve this depending on the use-case:

1. Using `using('default')` to explicitly target the primary instance for a specific query:

    ```python
    # Write data
    obj = MyModel.objects.create(field='value')

    # Read data from primary to avoid replication lag
    obj = MyModel.objects.using(DEFAULT_DB_ALIAS).get(id=obj.id)
    ```

2. Using a transaction explicitly with the default connection alias `transaction.atomic(using=DEFAULT_DB_ALIAS)`:

    ```python
    with transaction.atomic(using=DEFAULT_DB_ALIAS):
        # Write data
        obj = MyModel.objects.create(field='value')

        # Read data - will use primary due to open transaction
        obj = MyModel.objects.get(id=obj.id)
    ```

### Use of combined read-write methods

> [!WARNING]
> For performance-critical areas, some of Django's built-in queries should be avoided: `get_or_create`, `update_or_create`. These methods result in queries
> which always use the primary database instance.

Instead, it may be better to use multiple explicit queries (e.g. `.get` then `.create`) so that the optimal connection is used. However, take care to avoid the
replication lag issues described above.
