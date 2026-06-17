# Scheduling

Wagtail publishes pages using a management command. When run, this command publishes any pages which are due to be published.
It is expected to be run using an external scheduler (e.g. cron).

On the ONS infrastructure, we use the Kubernetes CronJob.

In other environments, such as the local one, we use [`APScheduler`](https://pypi.org/project/APScheduler/) to run a [continuous scheduler task](https://github.com/ONSdigital/dis-wagtail/blob/main/cms/core/management/commands/scheduler.py)
that triggers the [`publish_bundles`](https://github.com/ONSdigital/dis-wagtail/blob/main/cms/bundles/management/commands/publish_bundles.py) management command
every minute, and [`publish_scheduled_without_bundles`](https://github.com/ONSdigital/dis-wagtail/blob/main/cms/bundles/management/commands/publish_scheduled_without_bundles.py) every 5.

## `publish_bundles`

Is a management command that publishes [bundles](bundles.md) that are scheduled and ready to publish. Bundles are considered for publishing if their release date is in the past.

### `--include-future`

To reduce the impact of the process and infrastructure warm-up time, `publish_bundles` starts earlier than necessary and includes bundles which need to be published in the future. The command then waits until each bundle's release time, and then publishes it. Bundles due to be published in the past are still published immediately.

For example, for a release scheduled at `07:00`, `publish_bundles` will start shortly after `06:59` (it starts on odd-numbered minutes with `--include-future=60`), notice the bundle due at `07:00`, sleep for around 60 seconds (ie until it's `07:00`), then publish the bundle.

How far in the future bundles should be included is set with the `--include-future` option, which takes a number of seconds.

## `publish_scheduled_without_bundles`

Is a modified version of the Wagtail core [`publish_scheduled`](https://github.com/wagtail/wagtail/blob/main/wagtail/management/commands/publish_scheduled.py) management command that excludes any pages that are in an active bundle. Pages are considered for publishing if their publish date is in the past.

### `--include-future`

See `--include-future` on `publish_bundles` for more details. This functionality applies to pages due to be published or unpublished.
