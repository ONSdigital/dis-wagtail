# Notifications

## Email

Email notifications are sent:
- on [Wagtail workflows](https://guide.wagtail.org/en-latest/how-to-guides/configure-workflows-for-moderation/) changes
  That is, when a page is submitted for review, is accepted/rejected, or comments are added.
- for bundles
  - when teams are added
  - when the bundle is published

## Slack

Currently, we send Slack notifications to a Slack webhook when bundle statuses change.

### Environment variables

| Var                               | Notes                                                                                                                     |
|-----------------------------------|---------------------------------------------------------------------------------------------------------------------------|
| `SLACK_NOTIFICATIONS_WEBHOOK_URL` | Currently used by the [bundle](../custom-features/bundles.md) app to send notifications on status change, and publication |

