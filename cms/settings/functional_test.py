from .test import *  # noqa: F403  # pylint: disable=wildcard-import,unused-wildcard-import

REDIS_URL = "redis://localhost:16379"

DATABASES["default"]["PORT"] = DATABASES["read_replica"]["PORT"] = 15432  # noqa: F405

CMS_USE_SUBDOMAIN_LOCALES = False
