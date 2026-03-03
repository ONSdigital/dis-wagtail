# Search Service (via Kafka)

The CMS integrates with the Search Service by sending messages to the Kafka broker using the 'search-content-updated' (created or updated)
and 'search-content-deleted' (deleted) events, aligning with the `StandardPayload` / `ReleasePayload` / `content-deleted` schema definitions.

- [Generic Search proposal](https://officefornationalstatistics.atlassian.net/wiki/spaces/DIS/pages/60785600/Generic+Search+Proposal)
- [dp-search-data-extractor spec](https://github.com/ONSdigital/dp-search-data-extractor/blob/develop/specification.yml#L53)
- [dp-search-data-importer spec](https://github.com/ONSdigital/dp-search-data-importer/blob/30fb507e90f2cf1974ec0ca43bb0466307e2f112/specification.yml#L186)
- [Search metadata contract](https://github.com/ONSdigital/dis-search-upstream-stub/blob/main/docs/contract/resource_metadata.yml)
- [Search upstream service endpoints spec](https://github.com/ONSdigital/dis-search-upstream-stub/blob/main/specification.yml)

The CMS also provides a paginated Resource API endpoint with all published pages at `/v1/resources` if `CMS_RESOURCES_ENDPOINT_ENABLED` is set to `true`.
This is used by the search service for reindexing and is meant to be only accessible in the internal instance.

## Environment variables

| Var                                        | Notes                                                                                       |
| ------------------------------------------ | ------------------------------------------------------------------------------------------- |
| `SEARCH_INDEX_PUBLISHER_BACKEND`           | Set to `kafka` to enable send data to the Search service Kafka broker                       |
| `KAFKA_SERVERS`                            | A comma-separated list of Kafka broker URLs.                                                |
| `KAFKA_USE_IAM_AUTH`                       | Defaults to `false`. Set to `true` to enable IAM authentication.                            |
| `CMS_SEARCH_NOTIFY_ON_DELETE_OR_UNPUBLISH` | Defaults to `true`. Set to `false` to disable firing kafka events on deletion or unpublish. |
| `CMS_RESOURCES_ENDPOINT_ENABLED`           | Set to `true` to enable the Resource API endpoint.                                          |

## Developer notes

We use [kafka-python](https://pypi.org/project/kafka-python/) to send data to Kafka, and
[aws-msk-iam-sasl-signer-python](https://pypi.org/project/aws-msk-iam-sasl-signer-python/) to authenticate using IAM.

The implementation is in [`cms/search`](https://github.com/ONSdigital/dis-wagtail/tree/main/cms/search). The publisher
classes are defined in [`cms/search/publishers/kafka.py`](https://github.com/ONSdigital/dis-wagtail/blob/main/cms/search/publishers/kafka.py).

Messages are sent via [Django signal handlers](https://docs.djangoproject.com/en/5.2/topics/signals/#listening-to-signals) in [`cms/search/signal_handlers.py`](https://github.com/ONSdigital/dis-wagtail/blob/main/cms/search/signal_handlers.py),
specifically, on page publish, unpublish and delete.

The Resource API endpoint is powered by <abbr title="Django Rest Framework">[DRF](https://www.django-rest-framework.org/)</abbr> and can be found in [`cms/search/views.py`](https://github.com/ONSdigital/dis-wagtail/blob/main/cms/search/views.py)
