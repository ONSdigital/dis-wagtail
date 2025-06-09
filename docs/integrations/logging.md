# Logging

The CMS implements logging that conforms to the [ONS Logging standards](https://github.com/ONSdigital/dp-standards/blob/main/LOGGING_STANDARDS.md)

This is done by creating a custom log formatter classes ([ref](https://github.com/ONSdigital/dis-wagtail/blob/main/cms/core/logs.py)), and
setting up the [Django logging](https://docs.djangoproject.com/en/stable/topics/logging/) settings to [use them](https://github.com/ONSdigital/dis-wagtail/blob/main/cms/settings/base.py#L485).

## Developer notes

To start with, read the [Django logging](https://docs.djangoproject.com/en/stable/topics/logging/) documentation.

In most cases, one would

```python
# cms/path/to/my_module.py
import logging

logger = logging.getLogger(__name__)
...

logger.info("This is my log message")
```

To include extra data, use the `extra` keyword argument, which takes a dictionary with the extra data to pass on.

```python
# cms/path/to/my_module.py
import logging

logger = logging.getLogger(__name__)
...

logger.info("Extra data", extra={"data": 123})
```

You can see an example in `cms/bundles/management/commands/publish_bundles.py`:

```python
logger.info(
    "Publishing Bundle",
    extra={
        "bundle_id": bundle_id,
        "event": "publishing_bundle",
    },
)
```
