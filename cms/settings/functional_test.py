from .test import *  # noqa: F403  # pylint: disable=wildcard-import,unused-wildcard-import

REDIS_URL = "redis://localhost:16379"

DATABASES["default"]["PORT"] = DATABASES["read_replica"]["PORT"] = 15432  # noqa: F405

SEARCH_INDEX_PUBLISHER_BACKEND = "kafka"

# KAFKA_SERVERS = ["localhost:19094"]
