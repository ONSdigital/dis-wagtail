# Search Service (via Kafka)

The CMS integrates with the Search Service by sending messages to the Kafka broker using the 'search-content-updated' (created or updated)
and 'search-content-deleted' (deleted) events, aligning with the `StandardPayload` / `ReleasePayload` / `content-deleted` schema definitions.

- [dp-search-data-extractor spec](https://github.com/ONSdigital/dp-search-data-extractor/blob/develop/specification.yml#L53)
- [dp-search-data-importer spec]()https://github.com/ONSdigital/dp-search-data-importer/blob/30fb507e90f2cf1974ec0ca43bb0466307e2f112/specification.yml#L186
- [Search metadata contract](https://github.com/ONSdigital/dis-search-upstream-stub/blob/main/docs/contract/resource_metadata.yml)
- [Search upstream service endpoints spec](https://github.com/ONSdigital/dis-search-upstream-stub/blob/main/specification.yml)

The CMS also provides a paginated Resource API endpoint with all published pages at `/v1/resources/` in the public facing instance. This is
used by the search service for reindexing.

## Environment variables

| Var                                | Notes                                                                 |
| ---------------------------------- | --------------------------------------------------------------------- |
| `SEARCH_INDEX_PUBLISHER_BACKEND`   | Set to `kafka` to enable send data to the Search service Kafka broker |
| `KAFKA_CHANNEL_CREATED_OR_UPDATED` | `search-content-updated` as per spec                                  |
| `KAFKA_CHANNEL_DELETED`            | `search-content-deleted` as per spec                                  |
| `KAFKA_API_VERSION`                | Defaults to "3,5,1"                                                   |
