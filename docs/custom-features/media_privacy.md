# Media privacy

This project uses customised versions of Wagtail's `Image` and `Document` models to store and manage the
privacy of uploaded media files.

1. The privacy of an image or document cannot be changed manually via the Wagtail UI.
2. Images and documents are private by default, and will only be served to authenticated users with some level of permission on the media item whilst they have this privacy status (so previewing from Wagtail should still work as expected).
3. Where the storage backend supports it, files for private images and documents (and any renditions created from the original image) will have their access permissions updated at the storage level, preventing direct file access.
4. Images and documents only become public when they are referenced by blocks in page content, and that page is published.
5. When a page is unpublished, any public images or documents referenced solely by that page are made private again (references from other draft pages are ignored, as the media can easily be made public again when the draft page is published).

## Use of Wagtail's reference index

Wagtail's reference index is used to track when images and documents (and other objects) are referenced by pages and other objects.

Population of the reference index is automatically triggered by the `post_save` signal for all registered models.

When publishing or unpublishing a page (or other type of 'publishable' object), object-level changes are saved before any `published`, `page_published`, `unpublished` or `page_unpublished` signals are emitted. So, as long as we use these signals to review the privacy
of referenced media, we can be sure that the reference index will be up-to-date.

## Handling of file permission setting errors

Whilst file-permission setting requests are quite reliable in S3, they can fail occasionally (as with any web service).

Failed attempts are tracked using a `file_permissions_last_set` timestamp for each media item, which is only updated if all update requests for the media item were successful.

The `retry_file_permission_set_attempts` management command seeks out any media items with an outdated timestamp and attempts to update the files again.

The custom `PrivacySettingS3Storage` class logs failed file-setting attempts using the 'WARNING' log level, so should be available to review in most environments should issues occur.

## Compatibility with upstream caching

Because serve view responses and direct file urls can be cached, it's important that when the privacy of a media item changes, the cache
is invalidated for any affected URLs. In environments where Wagtail's front-end-cache app is configured, all relevant URLs should be collected into a batch and sent to the relevant backend to initiate purging.
