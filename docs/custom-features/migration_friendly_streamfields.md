# Migration-friendly StreamFields

This project uses a custom field class (`cms.core.fields.StreamField`) instead of the usual `wagtail.fields.StreamField` field for streamfield content. This customised field helps with a few things that we often struggle with on busy projects, especially in the early stages:

1. It keeps block definitions out of migration files, meaning the migrations themselves are much smaller, take less time to lint/format, and keeps the Django's `makemigrations` command nice and snappy.
2. Making changes to block definition no longer requires an accompanying database migration, leading to fewer migrations overall.
3. Making changes to the field's `verbose_name` value no longer requires a migration either, so you can re-label to your heart's content.

As you might guess, not including the block definitions in migrations means that, when writing a [Data Migration](https://docs.djangoproject.com/en/stable/topics/migrations/#data-migrations-1) the field behaves a little differently than the standard field. Because the block definitions are unavailable, it is not possible to turn raw data into a fully-fledged, renderable `StreamField` value in a data migration. However, you **CAN** access the raw streamfield data via the `obj.streamfield_name.raw_data` attribute, and update the value in the usual fashion (dumping the data to a string with `json.dumps()` and using that as the new field value).
