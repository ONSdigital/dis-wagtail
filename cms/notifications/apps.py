from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    name = "cms.notifications"

    def ready(self):
        import cms.notifications.signal_handlers
