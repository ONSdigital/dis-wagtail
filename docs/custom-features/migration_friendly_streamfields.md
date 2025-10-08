# Migration-friendly StreamFields

This project uses a custom field class (`cms.core.fields.StreamField`) instead of the usual `wagtail.fields.StreamField` field for streamfield content.
This customised field helps with a few things that we often struggle with on busy projects, especially in the early stages:

1. It keeps block definitions out of migration files, meaning the migrations themselves are much smaller, take less time to lint/format,
   and keeps the Django's `makemigrations` command nice and snappy.
2. Making changes to block definition no longer requires an accompanying database migration, leading to fewer migrations overall.
3. Making changes to the field's `verbose_name` value no longer requires a migration either, so you can re-label to your heart's content.

As you might guess, not including the block definitions in migrations means that,
when writing a [Data Migration](https://docs.djangoproject.com/en/stable/topics/migrations/#data-migrations-1) the field behaves a little differently
than the standard field. Because the block definitions are unavailable, it is not possible to turn raw data into a fully-fledged,
renderable `StreamField` value in a data migration. However, you **CAN** access the raw streamfield data via the `obj.streamfield_name.raw_data` attribute,
and update the value in the usual fashion (dumping the data to a string with `json.dumps()` and using that as the new field value).

---

## Behaviour when blocks are removed (orphaned data)

Removing a block from our custom StreamField does **not** delete its data immediately. The data remains until the page is interacted with.

### What actually happens

- The raw data stays in the database after the block is removed.
- On the **next save**, the data is dropped from the revisions table.
- On **publish**, it is also removed from the main page table.

Old data will only reappear if:

- the page hasn’t been saved or published since the block was removed, or
- an older revision (created before the removal) is restored.

If the block is later reintroduced, only those scenarios will surface the previous values.

### Cleanup considerations

- Orphaned data is not removed automatically.
- Once a page is saved or published, the data is dropped from the relevant records.
- Whether to remove it should be considered case by case.

If automatic cleanup becomes a priority, using the default `wagtail.fields.StreamField` may be simpler than extending the custom one.

Once the page models are stable and block changes are unlikely, reverting to the standard `StreamField` will be clearer and more predictable.
