# Notifications

## Email

Email notifications are sent:

- on [Wagtail workflows](https://guide.wagtail.org/en-latest/how-to-guides/configure-workflows-for-moderation/) changes
  That is, when a page is submitted for review, is accepted/rejected, or comments are added.
- for bundles
    - when teams are added
    - when the bundle is published

### Environment variables

| Var                  | Notes                                                                                                                                                               |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `EMAIL_BACKEND_NAME` | Possible values: `SES`, `SMTP`. For any other, defaults to Django's [console email backend](https://docs.djangoproject.com/en/stable/topics/email/#console-backend) |

When `EMAIL_BACKEND_NAME` is set to `SES`, the project uses [django-ses](https://pypi.org/project/django-ses/) to connect
to AWS SES (v2), automatically using [IAM](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles.html) roles/policies and
the configured `AWS_REGION`.

When `EMAIL_BACKEND_NAME` is set to `SMTP`, the project uses Django's [SMTP backend](https://docs.djangoproject.com/en/5.2/topics/email/#smtp-backend) and will use
the following environment variables, if set

| Var                   | Notes                                                                                                    |
| --------------------- | -------------------------------------------------------------------------------------------------------- |
| `EMAIL_HOST`          | Defaults to `localhost`. [Documentation](https://docs.djangoproject.com/en/5.2/ref/settings/#email-host) |
| `EMAIL_PORT`          | Defaults to `587`. [Documentation](https://docs.djangoproject.com/en/stable/ref/settings/#email-port)    |
| `EMAIL_HOST_USER`     | [Documentation](https://docs.djangoproject.com/en/stable/ref/settings/#email-host-user)                  |
| `EMAIL_HOST_PASSWORD` | [Documentation](https://docs.djangoproject.com/en/stable/ref/settings/#email-host-password)              |

## Slack

Currently, we send Slack notifications to a Slack webhook when bundle statuses change.

### Environment variables

| Var                               | Notes                                                                                                                     |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `SLACK_NOTIFICATIONS_WEBHOOK_URL` | Currently used by the [bundle](../custom-features/bundles.md) app to send notifications on status change, and publication |
