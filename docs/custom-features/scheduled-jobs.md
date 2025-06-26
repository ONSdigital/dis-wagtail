# Scheduling

Wagtail publishes pages using a management command. When run, this command publishes any pages which are due to be published.
It is expected to be run using an external scheduler (e.g. cron).

## Deployment

On the ONS infrastructure, we use the Kubernetes CronJob resource. The Kubernetes jobs run a small container which sends a request back to Wagtail to trigger the corresponding management command. Using a small container avoids the resource demands of a Pod dedicated to the management command and improves responsiveness.

This endpoint requires authentication, and is only available on the internal cluster. For security reasons, commands are run without arguments and do not take input from the requests.

## Local

In other environments, such as the local one, we use [`APScheduler`](https://pypi.org/project/APScheduler/) to run a [continuous scheduler task](https://github.com/ONSdigital/dis-wagtail/blob/main/cms/core/management/commands/scheduler.py)
that triggers the [`publish_bundles`](https://github.com/ONSdigital/dis-wagtail/blob/main/cms/bundles/management/commands/publish_bundles.py) management command
every minute, and [`publish_scheduled_without_bundles`](https://github.com/ONSdigital/dis-wagtail/blob/main/cms/bundles/management/commands/publish_scheduled_without_bundles.py) every 5.

### `publish_bundles`

Is a management command that publishes [bundles](bundles.md) that are scheduled and ready to publish.

### `publish_scheduled_without_bundles`

Is a modified version of the Wagtail core [`publish_scheduled`](https://github.com/wagtail/wagtail/blob/main/wagtail/management/commands/publish_scheduled.py)
management command that excludes any pages that are in an active bundle.
