# Database Read-Replica

Each deployed environment uses a primary-replica model for the database. Write queries are sent to the primary instance, whilst read queries are balanced
between a number of replicas. Replica instances are read-only - any write queries sent to them will return an error. For this reason, database migrations are
only run against the primary instance.

To ensure a consistent view of the database, the write instance is always used if there is an open transaction, even for reads.

Generally, a developer shouldn't need to worry about this configuration, or explicitly handle it - it is handled automatically by a database router (
`cms.core.db_router.ReadReplicaRouter`).

## Forcing the write database

In some situations, it may be necessary to force the write database instance be used for all database queries - even reads. To achieve this, you can use the `force_write_db_for_queryset` function on a given queryset:

```python
from cms.core.db_router import force_write_db_for_queryset

obj = MyModel.objects.create(field='value')

# Read data from default (write) DB alias to avoid replication lag
obj = force_write_db_for_queryset(MyModel.objects.all()).get(id=obj.id)
```

Alternatively, to require an entire block or function to use the write database, use `force_write_db`:

```python
from cms.core.db_router import force_write_db

with force_write_db():
    # Read data from default (write) DB alias
    obj = MyModel.objects.get(id=obj.id)

# It can also be used as a decorator:

@force_write_db()
def get_obj():
    # Read data from default (write) DB alias
    MyModel.objects.get(id=obj.id)
```

`force_write_db` supports being nested - only once the outer-most block has exited will the default behaviour be restored.

`force_write_db` is preferred over starting unnecessary transactions, as transactions both incur additional overhead, and change the behaviour of the system unnecessarily.

Note that `force_write_db` works only for queries executed within the block. Be careful when executing querysets, which are evaluated lazily:

```python

with force_write_db():
    qs = MyModel.objects.all()

# The queryset is evaluated with the `for`, meaning the query is executed outside the `force_write_db` block, and so uses the default behaviour.
for instance in qs:
    pass
```

## Coding considerations when using read-replicas

### Replication Lag

There is a small delay between writes to the primary instance and when those writes are visible on the replicas. This means that immediately (within the same request) attempting to read data from the replicas after writing it may return stale data, leading to race conditions and intermittent bugs.

This can be avoided by ensuring that any read-after-write operations are performed on the primary write instance, using one of the above utils. Note that this work-around is not necessary when **both** queries happen within the same transaction, since transactions are always handled using the write instance:

```python
from django.db import transaction
from cms.core.db_router import force_write_db_for_queryset


with transaction.atomic():
    obj = MyModel.objects.create(field='value')

    # This reads from the default (write) DB
    obj = MyModel.objects.get(id=obj.id)

    # This also reads from the default DB, but the `force_write_db_for_queryset` is unnecessary.
    obj = force_write_db_for_queryset(MyModel.objects.all()).get(id=obj.id)
```

This is only true for the _same_ transaction. If they're executed within different transactions, or only 1 is within a transaction, `force_write_db_for_queryset` is necessary.

### Use of combined read-write methods

> [!WARNING]
> For performance-critical areas, some of Django's built-in queries should be avoided: `get_or_create`, `update_or_create`. These methods result in queries
> which always use the primary database instance.
> Instead, it may be better to use multiple explicit queries (e.g. `.get` then `.create`) so that the optimal connection is used. However, take care to avoid the
> replication lag issues described above.
