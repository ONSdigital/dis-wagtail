# Dataset API

The CMS is currently integrating with the [public Dataset API](https://developer.ons.gov.uk/dataset/) to power related-dataset functionality and [bundling](../custom-features/bundles.md)
logic.

## Environment variables

| Var                | Notes                                      |
| ------------------ | ------------------------------------------ |
| `ONS_API_BASE_URL` | Defaults to https://api.beta.ons.gov.uk/v1 |

## Next

We will integrate with the [dis-bundle-api](https://github.com/ONSdigital/dis-bundle-api/), a backend service for
managing and publishing datasets and content as bundles, similar to Florence’s collections.

This will allow associating datasets with a release bundle in Wagtail by creating a corresponding bundle in the API, allowing
simultaneous release at the scheduled time.

### Links

- [Bundle API spec](https://github.com/ONSdigital/dis-bundle-api/blob/develop/swagger.yaml) (you can use https://generator.swagger.io/ to view it rendered)
- [Data API Tech proposal](https://confluence.ons.gov.uk/display/DIS/Bundles+%28Data+API%29+-+Technical+Executive+Proposal)
- [Dateset Publishing Requirements](https://confluence.ons.gov.uk/display/DIGPUB/Dataset+Publishing+Requirements)
