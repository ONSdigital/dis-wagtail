# Data Creation Scripts

## Overview

The `cms.test_data` app provides management commands for seeding and cleaning up test data during local development. It uses factory-boy and Faker to generate reproducible CMS content, and Pydantic to validate configuration.

The app is **not intended for production environments**.

It is controlled by the `CMS_TEST_DATA_ENABLED` environment variable and is enabled locally by default in `dev` and `test` settings. The environment variable can be used to enable it for load testing in a test environment.

## Supported Models

The following models can be created by the test data scripts:

| Model         | App            | Notes                                                                                   |
| ------------- | -------------- | --------------------------------------------------------------------------------------- |
| `CustomImage` | `cms.images`   | Wagtail images created in the root collection.                                          |
| `Dataset`     | `cms.datasets` | Each dataset is given a unique edition and version.                                     |
| `Topic`       | `cms.taxonomy` | Taxonomy topics, created under the root topic.                                          |
| `TopicPage`   | `cms.topics`   | Wagtail pages linked to a topic, with optional dataset links and "explore more" blocks. |

## Prerequisites

Ensure the app is enabled. In local development this is the default; otherwise, set the environment variable:

```
CMS_TEST_DATA_ENABLED=true
```

The `CMS_TEST_DATA_PREFIX` setting (defined in `cms/settings/base.py`) controls the prefix string added to all generated records. This prefix is how the delete command identifies test data.

## Usage

All commands are available as Makefile targets or can be run directly via `manage.py`.

### Viewing the Default Configuration

To see the default configuration (how many of each model will be created):

```bash
make test-data-show-default-config
```

To view the full JSON schema (useful when writing a custom config file):

```bash
make test-data-show-default-config SCHEMA=1
```

### Creating Test Data

```bash
make test-data-create
```

You will be prompted to confirm before data is created.

| Variable  | Default           | Description                                                                                   |
| --------- | ----------------- | --------------------------------------------------------------------------------------------- |
| `SEED`    | `4`               | Integer seed for deterministic output. The same seed and config always produce the same data. |
| `CONFIG`  | Built-in defaults | Path to a custom JSON configuration file.                                                     |
| `NOINPUT` | —                 | Set to `1` to skip the confirmation prompt.                                                   |

Examples:

```bash
# Use a specific seed
make test-data-create SEED=42

# Use a custom config file
make test-data-create CONFIG=path/to/config.json

# Skip the confirmation prompt (useful in scripts / CI)
make test-data-create NOINPUT=1
```

**Creation order:** images → datasets → topics. Topics reference previously created images and datasets, so they are created last.

All records are created inside a single database transaction. If anything fails, all changes are rolled back.

### Deleting Test Data

To preview what would be deleted (dry run):

```bash
make test-data-delete-dry-run
```

To delete all previously created test data:

```bash
make test-data-delete
```

To skip the confirmation prompt:

```bash
make test-data-delete NOINPUT=1
```

The delete command scans every model's `CharField` and `TextField` columns for values starting with `CMS_TEST_DATA_PREFIX`. Only records created by `create_test_data` will be matched. Cascading deletions and field updates (e.g. `SET_NULL`) are displayed before confirmation.

## Configuration

Configuration is validated with Pydantic. The default configuration is:

```json
{
    "images": { "count": 1 },
    "datasets": { "count": 1 },
    "topics": {
        "count": 3,
        "published_probability": 0.5,
        "revisions": 1,
        "datasets": 1,
        "dataset_manual_links": 0,
        "explore_more": 1
    }
}
```

### Configuration Reference

#### `images` / `datasets`

| Field   | Type                              | Default | Description                                                                                            |
| ------- | --------------------------------- | ------- | ------------------------------------------------------------------------------------------------------ |
| `count` | integer or `{"min": N, "max": M}` | `1`     | Number of records to create. A range produces a random count per run (deterministic for a given seed). |

#### `topics`

| Field                   | Type                              | Default | Description                                                                                                             |
| ----------------------- | --------------------------------- | ------- | ----------------------------------------------------------------------------------------------------------------------- |
| `count`                 | integer or `{"min": N, "max": M}` | `3`     | Number of topic pages to create.                                                                                        |
| `published_probability` | float (0–1)                       | `0.5`   | Probability that each topic page will be published.                                                                     |
| `revisions`             | integer or `{"min": N, "max": M}` | `1`     | Number of revisions to create per topic page.                                                                           |
| `datasets`              | integer or `{"min": 0, "max": M}` | `1`     | Number of existing datasets to link to each topic page via dataset lookup. Must not exceed `datasets.count`.            |
| `dataset_manual_links`  | integer (≥ 0)                     | `0`     | Number of manually-entered dataset links (title + URL) to add to each topic page.                                       |
| `explore_more`          | integer or `{"min": 0, "max": M}` | `1`     | Number of "explore more" blocks per topic page. Even-indexed blocks are internal links; odd-indexed are external links. |

### Validation Rules

- `count` must be a positive integer or a range where `min < max`.
- `topics.datasets` (highest possible value) must not exceed `datasets.count` (lowest possible value), since each dataset can only be linked once.
- The sum of `topics.datasets` and `topics.dataset_manual_links` must not exceed the maximum items per section (defined by `MAX_ITEMS_PER_SECTION` in the topics app).

## How It Works

### Prefixed Records

Every generated record has its title (or equivalent text field) prefixed with the value of `CMS_TEST_DATA_PREFIX`. This makes test data easy to identify and is the mechanism the delete command uses to find records to remove.

### Deterministic Seeding

The `--seed` option seeds both factory-boy's random generator and a dedicated Faker instance. Given the same seed and configuration, the commands produce identical data. The random state is saved and restored after the command completes, so running the command does not affect other test randomness.

### Signal Disconnection

During both creation and deletion, search index and publish-action signal receivers are temporarily disconnected to avoid unnecessary work. They are automatically reconnected when the operation completes, even if an error occurs. This includes:

- Search index `post_save` handlers
- Wagtail reference index update handlers
- Page published / unpublished / moved / deleted handlers
- Post-publish action handlers

### Tree Repair

The Wagtail topic tree (`Topic`, a treebeard `MP_Node`) can become inconsistent after bulk inserts or deletes. The commands call `Topic.fix_tree()` before creation and after deletion to ensure the tree remains valid.

This may be able to change after [PR 758](https://github.com/ONSdigital/dis-wagtail/pull/758) merges.
