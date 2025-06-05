# Scheduling

Wagtail publishes pages using a management command. When run, this command publishes any pages which are due to be published.
It is expected to be run using an external scheduler (e.g. cron).

We use [`APScheduler`](https://pypi.org/project/APScheduler/) to run a [continuous scheduler task](https://github.com/ONSdigital/dis-wagtail/blob/main/cms/core/management/commands/scheduler.py)
that triggers the [`publish_bundles`](https://github.com/ONSdigital/dis-wagtail/blob/main/cms/bundles/management/commands/publish_bundles.py) management command
every minute, and [`publish_scheduled_without_bundles`](https://github.com/ONSdigital/dis-wagtail/blob/main/cms/bundles/management/commands/publish_scheduled_without_bundles.py) every 5.

## `publish_bundles`

Is a management command that publishes [bundles](bundles.md) that are scheduled and ready to publish.

## `publish_scheduled_without_bundles`

Is a modified version of the Wagtail core [`publish_scheduled`](https://github.com/wagtail/wagtail/blob/main/wagtail/management/commands/publish_scheduled.py)
management command that excludes any pages that are in an active bundle.
