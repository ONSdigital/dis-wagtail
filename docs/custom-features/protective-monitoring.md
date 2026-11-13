# Protective monitoring

The CMS writes security-relevant events to stdout as structured JSON logs so a SIEM can ingest them. The format follows the [ONS logging standards](https://github.com/ONSdigital/dp-standards/blob/main/LOGGING_STANDARDS.md) (see [Logging](../integrations/logging.md)).

Events come from three sources:

1. **Audit events**: every Wagtail audit log entry (`PageLogEntry` and `ModelLogEntry`) is saved to the database as usual and also mirrored to stdout.
2. **Authentication events**: logins, logouts and failed logins, which go to stdout only.
3. **Denied access events**: 401/403 responses and admin redirects to the login page, which also go to stdout only.

## Audit events

### How mirroring works

[`cms/core/audit.py`](https://github.com/ONSdigital/dis-wagtail/tree/main/cms/core/audit.py) connects a `post_save` receiver to `wagtailcore.PageLogEntry` and `wagtailcore.ModelLogEntry`. When a new entry is created, it is logged to the `cms.audit` logger at `INFO` level. Updates to existing entries are ignored. The module is imported in `CoreConfig.ready()` so the receiver is always registered.

Because this hooks into the log entry models, anything that writes to Wagtail's audit log is picked up automatically. That covers Wagtail's built-in actions (`wagtail.create`, `wagtail.edit`, `wagtail.publish`, `wagtail.delete` and so on) and the custom actions listed below. To add a new audited action, register it with the [`register_log_actions`](https://docs.wagtail.org/en/stable/reference/hooks.html#register-log-actions) hook and call `wagtail.log_actions.log()`. No extra work is needed to get it to stdout.

Example output (formatted for readability):

```json
{
    "created_at": "2026-11-13T10:15:30.123Z",
    "namespace": "cms.audit",
    "severity": 3,
    "event": "Audit event: pages.edit_view",
    "data": {
        "event": "pages.edit_view",
        "object_type": "statistical article page",
        "object_id": "123",
        "object_label": "Labour market overview",
        "user_id": 4,
        "email": "editor@example.com",
        "data": {},
        "timestamp": "2026-11-13T10:15:30.120000+00:00"
    }
}
```

`user_id` and `email` are `null` for system actions such as scheduled publishing.

`severity` follows the logging standards: `0` is critical, `1` is error, `2` is warning and `3` is info. Audit and authentication events are `3`, except failed logins, which are `2`.

### Custom audit actions

On top of Wagtail's built-in actions, the project registers these:

| Action                                                                                                                                               | Logged when                                                                  | Cooldown |
| ---------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- | -------- |
| `pages.edit_view`                                                                                                                                    | A user opens the page editor (GET only)                                      | Yes      |
| `snippets.edit_view`                                                                                                                                 | A user opens a snippet editor (GET only)                                     | Yes      |
| `pages.preview_mode_used`                                                                                                                            | A user previews a saved page, per preview mode                               | Yes      |
| `wagtail.edit` (pages)                                                                                                                               | A page revision is saved, including autosave (built-in action, rate-limited) | Yes      |
| `content.chart_download`                                                                                                                             | A chart CSV is downloaded from a page revision                               | No       |
| `content.table_download`                                                                                                                             | A table CSV is downloaded from a page revision                               | No       |
| `topics.headline_figures_chooser.view`                                                                                                               | The headline figures chooser is opened for a topic page                      | No       |
| `bundles.edit_view`                                                                                                                                  | A user opens the bundle editor                                               | Yes      |
| `bundles.inspect`                                                                                                                                    | A user opens the bundle inspect view                                         | Yes      |
| `bundles.preview`                                                                                                                                    | A page or release calendar entry in a bundle is previewed                    | No       |
| `bundles.preview.attempt`                                                                                                                            | A user tries to preview bundle content without permission                    | No       |
| `bundles.update_status`, `bundles.approve`, `bundles.teams_changed`, `bundles.pages_changed`, `bundles.datasets_changed`, `bundles.schedule_changed` | Bundle changes (see [Bundles](bundles.md#logging))                           | No       |

Formatters for the core actions live in `register_core_log_actions` in [`cms/core/wagtail_hooks.py`](https://github.com/ONSdigital/dis-wagtail/tree/main/cms/core/wagtail_hooks.py). Bundle actions are registered in [`cms/bundles/wagtail_hooks.py`](https://github.com/ONSdigital/dis-wagtail/tree/main/cms/bundles/wagtail_hooks.py) and topic actions in [`cms/topics/wagtail_hooks.py`](https://github.com/ONSdigital/dis-wagtail/tree/main/cms/topics/wagtail_hooks.py).

### Cooldown

Some actions happen far more often than anyone needs to see them. Opening the editor, refreshing a preview or autosaving can each produce dozens of identical entries a minute. These actions go through a cooldown so the same user only generates one entry per object within a time window.

The window is set by `CMS_AUDIT_LOG_COOLDOWN_SECONDS` (env var of the same name, default `30`). Views and models read it through an `audit_log_cooldown_seconds` attribute, so tests can override it per class.

The logic is the same everywhere:

1. Build a cache key from the action, the object and the user.
2. If the key is in the cache, skip the log entry.
3. Otherwise, write the log entry and set the key with a timeout of `CMS_AUDIT_LOG_COOLDOWN_SECONDS`.

Suppressed requests do not refresh the key, so the window is fixed rather than sliding. A user who stays on the editor and keeps refreshing gets one entry every 30 seconds, not one entry in total.

| Action                    | Cache key                                                   | Where                                  |
| ------------------------- | ----------------------------------------------------------- | -------------------------------------- |
| `pages.edit_view`         | `page_edit_view_log:{page_id}:{user_id}`                    | `before_edit_page` hook                |
| `snippets.edit_view`      | `snippet_edit_view_log:{model_label}:{object_id}:{user_id}` | `before_edit_snippet` hook             |
| `pages.preview_mode_used` | `preview_page_log:{page_id}:{user_id}:{mode}`               | `BasePage._log_preview()`              |
| `wagtail.edit` (pages)    | `page_edit_save_log:{page_id}:{user_id or "none"}`          | `BasePage.save_revision()`             |
| `bundles.edit_view`       | `bundle_edit_log:{bundle_id}:{user_id}`                     | `BundleEditView._log_bundle_view()`    |
| `bundles.inspect`         | `bundle_inspect_log:{bundle_id}:{user_id}`                  | `BundleInspectView._log_bundle_view()` |

Each user, object and (for previews) preview mode gets its own window. Two editors on the same page are both logged, and switching preview mode is logged straight away.

#### Things to be aware of

- **Page and snippet edit views only log GET requests.** Saving the form is a POST and is covered by `wagtail.edit` instead. The bundle edit and inspect views log on every request to `dispatch`.
- **Only page saves are rate-limited.** `BasePage.save_revision()` turns `log_action` off when the key is already set, so the revision is still saved but no `wagtail.edit` entry is written. Other actions logged during the save (such as publishing) are unaffected.
- **Reverts are never suppressed.** When `previous_revision` is passed, Wagtail logs `wagtail.revert`. That is a deliberate action, so the cooldown is skipped.
- **Previews of unsaved pages are not logged**, because there is no primary key to log against.
- **The cooldown uses the default cache.** In hosted and dev environments that is Redis, so the window is shared across processes and containers. Redis errors are ignored (`IGNORE_EXCEPTIONS`), so if Redis is down every cache lookup misses and every event is logged. The cooldown fails open: you get more entries, never fewer. The test settings use `DummyCache`, which means the cooldown never applies in tests unless a test overrides `CACHES` (see `cms/core/tests/test_edit_save_audit.py`).

Only use the cooldown for high-volume, low-risk "viewed" or autosave-style events. Anything that changes state or signals possible misuse (downloads, denied previews, publishing) should be logged every time.

### Known gaps

Wagtail's multiple-upload views for images and documents (the default upload UI) do not create `wagtail.create` log entries, so those uploads are not audited. This is documented by tests in `cms/images/tests/test_audit.py` and `cms/documents/tests/test_audit.py`.

## Authentication events

Handlers in [`cms/users/signal_handlers.py`](https://github.com/ONSdigital/dis-wagtail/tree/main/cms/users/signal_handlers.py) listen to Django's auth signals and log to the `cms.users` logger:

| Event               | Level     | Fields                                         |
| ------------------- | --------- | ---------------------------------------------- |
| `user_logged_in`    | `INFO`    | `user_id`, `email`, `ip_address`, `user_agent` |
| `user_logged_out`   | `INFO`    | `user_id`, `email`, `ip_address`, `user_agent` |
| `user_login_failed` | `WARNING` | `username`, `ip_address`, `user_agent`         |

None of these are written to the database.

## Denied access events

`UnauthorizedAccessLoggingMiddleware` in [`cms/core/middleware.py`](https://github.com/ONSdigital/dis-wagtail/tree/main/cms/core/middleware.py) logs denied requests to the `cms.security` logger at `WARNING` level. It sits after the auth middleware so `request.user` is available. It is only added to `MIDDLEWARE` in internal environments (`IS_EXTERNAL_ENV=False`), so external environments do not emit these events.

A request counts as denied when:

- the response is a 401 or 403
- an admin URL redirects to the Wagtail or Django login URL, which is what Wagtail does for anonymous users and users without admin access
- an admin URL redirects to the admin home with Wagtail's "Sorry, you do not have permission to access this area." error message queued

The login, logout and password reset views are exempt, along with the editing session ping and release endpoints, which the edit page calls on its own after a logout or session expiry.

The event is `unauthorized access attempt` for authenticated users and `unauthenticated access attempt` for anonymous ones. These entries carry `"classification": "PROTECTIVE_MONITORING"` and an `http` block at the top level of the JSON, plus an `auth` block (the user's external ID, falling back to the internal ID) when the user is logged in:

```json
{
    "created_at": "2026-11-13T10:15:30.123Z",
    "namespace": "cms.security",
    "severity": 2,
    "event": "unauthorized access attempt",
    "classification": "PROTECTIVE_MONITORING",
    "http": {
        "host": "localhost:8000",
        "method": "GET",
        "path": "/admin/users/",
        "query": "",
        "scheme": "http",
        "started_at": "2026-11-13T10:15:30.100000+00:00",
        "status_code": 302,
        "port": 8000
    },
    "auth": { "identity": "f1d2c3...", "identity_type": "user" },
    "data": {
        "event_type": "unauthorized access attempt",
        "user_agent": "Mozilla/5.0 ...",
        "internal_user_id": 4,
        "email": "editor@example.com",
        "ip_address": "127.0.0.1"
    }
}
```

These events are not stored in the database.

## Other events

Opening the dataset chooser with unpublished datasets (the default, and always the case when choosing for a bundle) logs `Unpublished datasets requested` with the username. See `DatasetBaseChooseViewMixin` in [`cms/datasets/views.py`](https://github.com/ONSdigital/dis-wagtail/tree/main/cms/datasets/views.py).

## Configuration

| Setting                          | Default | Description                                                   |
| -------------------------------- | ------- | ------------------------------------------------------------- |
| `CMS_AUDIT_LOG_COOLDOWN_SECONDS` | `30`    | Cooldown window for rate-limited audit actions, in seconds    |
| `LOG_AS_JSON`                    | auto    | Output JSON logs. Defaults to `true` when stdout is not a TTY |

## Tests

- `cms/core/tests/test_audit.py`: mirroring log entries to stdout
- `cms/core/tests/test_edit_save_audit.py`: `wagtail.edit` cooldown on page saves
- `cms/core/tests/test_preview_audit.py`: preview logging and cooldown
- `cms/core/tests/test_wagtail_hooks.py`: page and snippet edit view logging
- `cms/core/tests/test_middleware.py`: denied access logging
- `cms/users/tests/test_signal_handlers.py`: authentication events
- `cms/images/tests/test_audit.py`, `cms/documents/tests/test_audit.py`: media audit entries

## Related documentation

- [Wagtail audit log](https://docs.wagtail.org/en/stable/extending/audit_log.html)
- [`register_log_actions` hook](https://docs.wagtail.org/en/stable/reference/hooks.html#register-log-actions)
- [Logging](../integrations/logging.md)
- [Bundles](bundles.md)
