# Locked Migrate

When the application starts up, it attempts to run migrations. This ensure that an application is always running with a known migration state (either its current state, or forward). Since multiple containers may be starting at once, this can result in multiple `manage.py migrate` commands running in parallel. Django doesn't do any locking itself on this, so the only locking is on each database query, which can result in errors or a corrupt database schema.

To work around this, there's a custom `locked_migrate` management command. This command uses a [PostgreSQL Advisory Lock](https://www.postgresql.org/docs/current/functions-admin.html#FUNCTIONS-ADVISORY-LOCKS) to ensure only a single `migrate` command can run.

1. First, check if there are any migrations to run. This avoids the need to lock on or wait for the lock if there's nothing to do. This can be skipped with `--skip-unapplied-check`
2. If the lock is free, acquire it and run `migrate`
3. If the lock is held, wait for up to `--timeout`. If the lock frees during that time, the process acquires the lock and runs `migrate` as above. If the lock times out, the process terminates.

Advisory locks are automatically released when the connections is terminated. If multiple processes are waiting for the lock, the first is given the lock (First in, first out).

> [!WARNING]
> Unless absolutely necessary, `locked_migrate` should always be used. Running `manage.py migrate` directly is still supported, however does not do any locking checks. Ensure no other migration commands are running before running this.
