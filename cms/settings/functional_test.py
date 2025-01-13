import copy

from .test import *  # noqa: F403  # pylint: disable=wildcard-import,unused-wildcard-import

DATABASES = {
    "default": dj_database_url.config(default="postgres://ons:ons@localhost:15432/ons"),  # noqa: F405
}
DATABASES["read_replica"] = copy.deepcopy(DATABASES["default"])

REDIS_URL = "redis://localhost:16379"
