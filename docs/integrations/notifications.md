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

The CMS is integrated with Slack to send notifications about important events, such as when a bundle is published or when a scheduled release is approaching.

### Environment variables

| Var                         | Notes                                                                                                                                    |
| --------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `SLACK_BOT_TOKEN`           | The token for the Slack bot that will be used to send notifications. [Documentation](https://docs.slack.dev/tools/python-slack-sdk/web/) |
| `SLACK_PUBLISH_LOG_CHANNEL` | The ID of the Slack channel where logs will be sent.                                                                                     |
| `SLACK_ALARM_CHANNEL`       | The ID of the Slack channel where alarms will be sent.                                                                                   |

### Technical details

The implementation stores the timestamp for most messages inside a bundle using the `slack_notification_ts` field, so that it can update the same message instead of sending a new one every time.

### Testing and debugging

In order to test the Slack integration, you may need to create your own workspace and bot, and set the appropriate environment variables.

This will allow you to see the notifications in your own Slack channels and verify that the integration is working correctly.
