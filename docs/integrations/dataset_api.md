# Dataset API

The CMS is currently integrating with the [public Dataset API](https://developer.ons.gov.uk/dataset/) to power related-dataset functionality and [bundling](../custom-features/bundles.md)
logic.

## Environment variables

| Var                     | Notes                                               |
| ----------------------- | --------------------------------------------------- |
| `DATASETS_BASE_API_URL` | Defaults to https://api.beta.ons.gov.uk/v1/datasets |

## Next

We will integrate with the [dis-bundle-api](https://github.com/ONSdigital/dis-bundle-api/), a backend service for
managing and publishing datasets and content as bundles, similar to Florence’s collections.

This will allow associating datasets with a release bundle in Wagtail by creating a corresponding bundle in the API, allowing
simultaneous release at the scheduled time.

## Topics

Dataset links on pages should now be served under their topic, e.g. `/inflationandpriceindices/datasets/cpih01` so the CMS tracks the topic it belongs to.

The dataset detail endpoint should contain a list of topic IDs under the `topics` key. This should always have the primary topic as the first item in the list.
Older dataset schema had a single `canonical_topic` field, which we can check as a fallback in the event the new field is not present or is empty.

In the event we either recieve no topic, or the topic does not exist in our local database we fall back to the previous, deprecated `/datasets/cpih01` url style.

### Bundles

When a dataset is associated with a bundle, the CMS will attempt to verify the local dataset metadata against the bundle API.
If the local data is stale vs the API we will update the local data, block approval and show a message to the user warning them of the change and asking them to re-confirm the approval with the udpated metadata.

### Links

- [Bundle API spec](https://github.com/ONSdigital/dis-bundle-api/blob/develop/swagger.yaml) (you can use https://generator.swagger.io/ to view it rendered)
- [Data API Tech proposal](https://officefornationalstatistics.atlassian.net/wiki/spaces/DIS/pages/60786954/Bundles+Data+API+-+Technical+Executive+Proposal)
- [Dateset Publishing Requirements](https://officefornationalstatistics.atlassian.net/wiki/spaces/DIGPUB/pages/52396856/Dataset+Publishing+Requirements)
