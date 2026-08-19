# Post-publish Actions

## Table of Contents

- [Overview](#overview)
    - [Action types](#action-types)
- [Architecture](#architecture)
    - [Signal-driven triggering](#signal-driven-triggering)
    - [Registry](#registry)
    - [Model](#model)
    - [Pages published outside a bundle](#pages-published-outside-a-bundle)
- [Parallel execution](#parallel-execution)
    - [Thread pool executor](#thread-pool-executor)
    - [Submission via `transaction.on_commit`](#submission-via-transactionon_commit)
    - [Fork safety](#fork-safety)
    - [Bundle notification sequencing](#bundle-notification-sequencing)
- [Connection pool management](#connection-pool-management)
    - [psycopg connection pooling](#psycopg-connection-pooling)
    - [Releasing connections between operations](#releasing-connections-between-operations)
    - [Write database routing](#write-database-routing)
- [Timeout and graceful shutdown](#timeout-and-graceful-shutdown)
    - [Timeout](#timeout)
    - [Gunicorn timeout](#gunicorn-timeout)
    - [Shutdown procedure](#shutdown-procedure)
- [Retry mechanism](#retry-mechanism)
- [Configuration reference](#configuration-reference)
- [Key files](#key-files)
- [Todos](#todos)

Post-publish actions are tasks that run asynchronously after pages are published as part of a bundle. They allow side effects such as updating search indexes or changing S3 ACLs to happen in parallel, without blocking the publishing process.

> [!IMPORTANT]
> Currently, all functionality described here applies to **pages published as part of bundles**. See [Pages published outside a bundle](#pages-published-outside-a-bundle) and [Todos](#todos) for more details.

## Overview

When a bundle is published, each page triggers registered post-publish actions. These actions are tracked as `PostPublishAction` model instances with status progression (`READY` → `RUNNING` → `SUCCESSFUL` / `FAILED`) and are executed concurrently using thread pools.

### Action types

Actions are registered via a decorator or function call:

- **`SEARCH_UPDATED`** — notifies the search service that a page has been created or updated (see `cms/search/signal_handlers.py`).
- **`S3_ACL`** — updates S3 object ACLs for private media associated with the page (see `cms/private_media/signal_handlers.py`).

New action types can be added by defining a handler that accepts `(page: Page, bundle: Bundle | None)` and registering it with `@post_publish_action(PostPublishActionType.MY_TYPE)` or `register_post_publish_action(...)`.

## Architecture

### Signal-driven triggering

Publishing is initiated either by the `publish_bundles` management command, which runs on a cron schedule, or via a manual publish via the Wagtail admin.

When a bundle's pages are published, Wagtail's `page_published` signal fires. A context manager (`enqueue_post_publish_actions_for_bundle`) sets the active bundle via a `ContextVar`, so the signal handler knows which bundle to associate with each action.

We allow the `page_published` signal to fire for each page and enqueue the action as this allows Wagtail to handle crawling for aliases. This ensures we won't have undue maintenance burden if future updates move more logic into signals.

```
publish_bundles command / manual publish in wagtail admin
  └─ publish_bundle(bundle) # clear any possible previous actions for bundle
       └─ enqueue_post_publish_actions_for_bundle(bundle)  # ContextManager, sets bundle in ContextVar
            └─ page.save_revision().publish()
                 └─ page_published signal
                      └─ run_post_publish_actions_for(page, bundle)
                           └─ PostPublishAction.objects.update_or_create(...)
                                └─ action.enqueue()
```

### Registry

`cms/post_publish_actions/registry.py` maintains a mapping of `PostPublishActionType` → handler callable. Handlers receive `(page, bundle)` and perform the side effect. Registration happens at app startup (in `signal_handlers.py` / `apps.py`).

### Model

`PostPublishAction` (`cms/post_publish_actions/models.py`) records each action with:

| Field           | Purpose                                                    |
| --------------- | ---------------------------------------------------------- |
| `action_type`   | The type of action (e.g. `S3_ACL`, `SEARCH_UPDATED`)       |
| `bundle`        | FK to the publishing bundle                                |
| `page`          | FK to the published page                                   |
| `status`        | Current state (`READY`, `RUNNING`, `SUCCESSFUL`, `FAILED`) |
| `failed_reason` | Exception detail on failure                                |
| `enqueued_at`   | When the action was created                                |
| `finished_at`   | When execution completed                                   |
| `duration`      | How long the handler took                                  |
| `timed_out_at`  | Set if the action was marked as timed out                  |
| `retry_count`   | Number of retry attempts                                   |

There are two unique constraints on the model as the bundle field is nullable.

| Constraint | Condition | Guarantee |
|`post_publish_actions_bundle_page_type`| `bundle IS NOT NULL` | One action per `(bundle, page, action_type)` |
|`post_publish_actions_page_type`| `bundle IS NULL` | One action per `(page, action_type)` |

### Pages published outside a bundle

When a page is published without an active bundle context, all registered handlers are called synchronously in the `page_published` signal handler.

This means that currently for non-bundle publishes

- Actions are blocking and sequential
- There is no status tracking, timeout or retry mechanism

This is consistent with existing behaviour, and planned to be worked on in future (see [Todos](#todos)).

## Parallel execution

### Thread pool executor

Post-publish actions for bundles run in a `ThreadPoolExecutor` rather than sequentially. This reduces total time taken for bundle publishing with larger numbers of pages, as we can concurrently run multiple IO bound actions.

Two separate thread pools are used:

| Executor | Setting                                   | Default Pool Size | Purpose                                         |
| -------- | ----------------------------------------- | ----------------- | ----------------------------------------------- |
| Main     | `BUNDLE_POST_PUBLISH_CONCURRENCY`         | 6                 | Runs the post-publish action handlers           |
| Support  | `BUNDLE_POST_PUBLISH_SUPPORT_CONCURRENCY` | 3                 | Runs ancillary tasks (e.g. Slack notifications) |

Separating the pools ensures that notification work cannot starve the main action workers and vice-versa.

### Submission via `transaction.on_commit`

Actions are submitted to the executor inside `transaction.on_commit(...)`. This guarantees that the publishing transaction has been committed — and therefore the page's published state is visible to the executor threads — before any action handler reads from the database.

Typically, we will always also use the `force_write_db` helper decorator to ensure that the action handler gets the latest data from the write database, rather than a read replica that may be lagging behind.

### Fork safety

The executors are rebuilt in child processes after a `fork()` via `os.register_at_fork(after_in_child=...)`, ensuring that Gunicorn pre-fork workers get their own clean thread pools.

### Bundle notification sequencing

Although actions run in parallel, Slack notifications for a given bundle are sequenced.

For scheduled publishes, `run_bundle_notification_in_support_executor` chains notification futures per bundle ID, so messages arrive in the correct order even when multiple bundles are published in the same run.

For manual publishes `run_after_hook` is used to enqueue a notification to the support executor after the publish runs.

## Connection pool management

Running post-publish actions in threads introduces contention on the database connection pool. Several strategies are used to keep connection usage low:

### psycopg connection pooling

Django's psycopg backend is configured with a connection pool (`min_size=1`, `max_size=3` by default). Read and write replicas can have independent pool sizes via:

- `DB_POOL_MAX_SIZE` — default max pool size (default: `3`)
- `DB_POOL_MAX_SIZE_WRITE` — override for the write database
- `DB_POOL_MAX_SIZE_READ` — override for the read replica

### Releasing connections between operations

- `close_old_connections()` is called **before and after** each executor task in `_executor_wrapper`, following Django's pattern for threaded work.
- An additional `close_old_connections()` call is made **just before** the action handler runs in `run_action`. If the handler doesn't touch the database (e.g. an HTTP call to an external service), the connection is freed for another thread to use during that time.
- `release_db_connections()` (in `cms/core/utils.py`) provides a transaction-safe alternative to `close_old_connections`. It only closes connections that are not in an atomic block and are in autocommit mode, making it safe to call from within polling loops without risking in flight transactions.

### Write database routing

Post-publish actions use `@force_write_db()` to ensure status updates go to the write database, not the read replica. This avoids replication lag issues when polling for completion.

## Timeout and graceful shutdown

### Timeout

The system uses a configurable timeout (`BUNDLE_POST_PUBLISH_TIMEOUT_SECONDS`, default: `110` seconds) that governs:

1. How long the polling loop in `as_completed_actions_by_bundle` waits for actions to finish.
2. How long the `retry_post_publish_actions` command waits for retried actions.
3. When the shutdown warning is logged in `executor_stop_and_wait`.

The 110-second default is chosen to fit comfortably within a 2-minute cron interval.

### Gunicorn timeout

`gunicorn.conf.py` sets `graceful_timeout` to `BUNDLE_POST_PUBLISH_TIMEOUT_SECONDS`, allowing in-flight post-publish threads to complete before Gunicorn forcefully kills the worker during deployments or restarts.

### Shutdown procedure

`executor_stop_and_wait` initiates a non-blocking shutdown of both thread pools, then polls for thread completion with progress logging. If threads are still running near the timeout boundary, an error is logged to alert operators.

## Retry mechanism

The `retry_post_publish_actions` management command (intended to run on a separate cron schedule) finds actions that:

- Were enqueued more than `2× BUNDLE_POST_PUBLISH_TIMEOUT_SECONDS` ago, **and**
- Are in a `RUNNING`, `FAILED`, or `READY` state (i.e. they appear stuck or explicitly failed).

These actions are re-enqueued up to `BUNDLE_POST_PUBLISH_MAX_RETRIES` times (default: `3`). Actions that exhaust their retries are logged as errors for manual investigation.

If a bundle is re-published, any actions are deleted and re-created so we don't leave stale actions (linked to removed pages, at their retry limit etc.).

## Configuration reference

| Setting                                       | Default                            | Description                                                      |
| --------------------------------------------- | ---------------------------------- | ---------------------------------------------------------------- |
| `BUNDLE_POST_PUBLISH_TIMEOUT_SECONDS`         | `110`                              | Maximum time to wait for actions to complete                     |
| `BUNDLE_POST_PUBLISH_CONCURRENCY`             | `6`                                | Thread pool size for action handlers                             |
| `BUNDLE_POST_PUBLISH_SUPPORT_CONCURRENCY`     | `3`                                | Thread pool size for support tasks                               |
| `BUNDLE_POST_PUBLISH_POLL_FREQUENCY`          | `5`                                | Seconds between completion polls                                 |
| `BUNDLE_POST_PUBLISH_MAX_RETRIES`             | `3`                                | Max retry attempts for failed actions                            |
| `BUNDLE_POST_PUBLISH_ACTION_SUBMIT_ON_COMMIT` | `True`                             | Whether to use `transaction.on_commit` (set to `False` in tests) |
| `DB_POOL_MAX_SIZE`                            | `3`                                | Default database connection pool max size                        |
| `DB_POOL_MAX_SIZE_WRITE`                      | (falls back to `DB_POOL_MAX_SIZE`) | Pool max size for the write database                             |
| `DB_POOL_MAX_SIZE_READ`                       | (falls back to `DB_POOL_MAX_SIZE`) | Pool max size for the read replica                               |

## Key files

| File                                                                         | Purpose                                               |
| ---------------------------------------------------------------------------- | ----------------------------------------------------- |
| `cms/post_publish_actions/models.py`                                         | `PostPublishAction` model and status/type enums       |
| `cms/post_publish_actions/executor.py`                                       | Thread pool executors, task wrappers, shutdown logic  |
| `cms/post_publish_actions/registry.py`                                       | Action handler registry                               |
| `cms/post_publish_actions/signal_handlers.py`                                | Wagtail signal integration and bundle context manager |
| `cms/post_publish_actions/utils.py`                                          | Completion polling, Slack notification orchestration  |
| `cms/post_publish_actions/management/commands/retry_post_publish_actions.py` | Retry management command                              |
| `cms/bundles/management/commands/publish_bundles.py`                         | Bundle publishing orchestration                       |
| `cms/bundles/utils.py`                                                       |                                                       |
| `cms/search/signal_handlers.py`                                              | `SEARCH_UPDATED` action handler                       |
| `cms/private_media/signal_handlers.py`                                       | `S3_ACL` action handler                               |
| `cms/core/utils.py`                                                          | `release_db_connections` utility                      |
| `gunicorn.conf.py`                                                           | Graceful timeout configuration                        |

## Todos

Bundles were the first use case for concurrent post-publish actions, but in future we intend to support the following.

- Individual page publishes (outside of bundles)
- Page unpublishes (both inside and outside of bundles)

This will also include new registry actions for custom cache purging (in development on feature branch `feature-frontend-cache-invalidation`).
