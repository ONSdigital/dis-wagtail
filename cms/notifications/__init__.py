from functools import cache

# from django.conf import settings
from .notifiers import AWS_SES_Notifier, LogNotifier


@cache
def get_notifier() -> AWS_SES_Notifier | LogNotifier:
    """Return the configured notification backend."""
    # backend = settings.EMAIL_BACKEND
    # if backend == "django_ses.SESBackend":
    #     return AWS_SES_Notifier()
    print("Using LogNotifier as the default notification backend.")
    return LogNotifier()
