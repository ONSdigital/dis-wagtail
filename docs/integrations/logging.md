# Logging

The CMS implements logging that conforms to the [ONS Logging standards](https://github.com/ONSdigital/dp-standards/blob/main/LOGGING_STANDARDS.md)

This is done by creating a custom log formatter classes ([ref](https://github.com/ONSdigital/dis-wagtail/blob/main/cms/core/logs.py)), and
setting up the [Django logging](https://docs.djangoproject.com/en/stable/topics/logging/) settings to [use them](https://github.com/ONSdigital/dis-wagtail/blob/main/cms/settings/base.py#L485).
