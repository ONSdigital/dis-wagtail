# Media privacy

This project uses customised versions of Wagtail's `Image` and `Document` models to store and manage the
privacy of uploaded media files, so that potentially sensitive media isn't leaked to the public before it's ready.

## The basic premise

1. Images and documents are 'private' by default, and will only be served to authenticated users with some level of permission on the media item.
2. They only become 'public' when a page referencing them is published.
3. When a live page unpublished, any images or documents referenced soley by that page (i.e. not used on any other live pages) are made private again.

These cases (and more) are covered by integration tests in [cms/private_media/tests/test_signal_handlers.py](https://github.com/ONSdigital/dis-wagtail/tree/main/cms/private_media/tests/test_signal_handlers.py).

## Setting of file-level permissions

In environments where storage service supports it (e.g. hosted environments using a S3 for media storage), attempts are made to set file-level permissions to reflect the privacy of the media item. This happens automatically when an image, rendition, or document is saved for the first time, and also when its privacy is altered as the result of another action (e.g. a referencing page being published or unpublished).

The responsibility of setting file-level permissions in hosted environments falls to the `cms.private_media.storages.PrivacySettingS3Storage` class, which implements the `make_public()` and `make_private()` methods.

In local dev environments, the permission-setting attempts themselves are skipped, but log entries are generated with the level 'INFO' in place of each attempt, so  you can get a sense of what would have happen in a hosted environment, for example:

```
INFO:cms.private_media.bulk_operations:Skipping file permission setting for: /media/images/2024/12/09/image.jpg
```

Whenever the privacy of a media item is altered, it's `privacy_last_changed` timestamp field is updated and saved to the database alongside other changes.
If no errors occurred during the file-updating process, the media items' `file_permissions_last_set` timestamp will also be updated and saved. Because the file-permission setting happens later in the update process, the `file_permissions_last_set` timestamp should always be greater than the `privacy_last_changed` value when no errors occurred.

### Performance considerations

Because media item privacy is often updated in-bulk (e.g. making all images referenced by a page public when it's published), and each media item can have multiple files associated with it (e.g. multiple renditions of an image, each with it's own file), file-level permission setting has to be as performant as possible, and not choke if an errors occurs.

Since media-hosting services don't provide a way to set file-level permissions in bulk, the best we can do is to make sure the individual requests don't block each other, so we use a `ThreadPoolExecutor` to run them in parallel.

If an error occurred whilst attempting to get or set file-level permissions, the error is logged, but processing continues with the next item in the sequence.

### Tracking of unsuccesful permission-setting attempts

Whilst file-permission setting requests are quite reliable in S3, they can fail occasionally (as with any web service).

Because a media item's `file_permissions_last_set` timestamp is only updated when all file-permission setting attempts were successful, for media items with outdated file permissions, the `file_permissions_last_set` timestamp will trail behind the `privacy_last_changed` value.

For an individual object, the `file_permissions_are_outdated()` method will return `True` if the `file_permissions_last_set` timestamp is less than the `privacy_last_changed` value. This is used in a few places to vary the behaviour. Specifically, the `href` value for images will continue to point to the media serve view, so that it can still be served to users, and the serve view checks it before redirecting users to the direct file URL.

The timestamp values can also be used to identify affected media items in bulk using the Django ORM, and reattempt the permission-setting process. This is the approach taken by the `retry_file_permission_set_attempts` management command, which runs regularly (every 5 minutes) in hosted environments to help keep file permissions up-to-date.

## Use of Wagtail's reference index

Wagtail's [reference index](https://docs.wagtail.org/en/stable/advanced_topics/reference_index.html) is used to track when images and documents (and other objects) are referenced by pages and other objects.

The reference index is automatically populated via handlers connected to the `post_save` signal for all registered models.

When publishing or unpublishing a page (or other type of 'publishable' object), object-level changes are saved before any `published`, or `unpublished` or signals are emitted. So, as long as we use these signals to review the privacy
of referenced media, we can be sure that the reference index will be up-to-date.

## Compatibility with upstream caching

Because serve view responses and direct file urls can be cached, it's important that when the privacy of a media item changes, the cache
is invalidated for any affected URLs. In environments where Wagtail's front-end-cache app is configured, all relevant URLs should be collected into a batch and sent to the relevant backend to initiate purging.

## Adding private media support to a new model

To add private media support to a new model, simply include the `PrivateMediaMixin` mixin in the model's parent classes, and then implement a `get_privacy_controlled_files()` method which returns the values of all of the file field values you wish to protect.

For example, if you had a `Chart` snippet model with `thumbnail_image` and `data_csv` fields that you wanted to protect, the final class definition might look like this:

```python

from typing import TYPE_CHECKING, Iterator
from django.db import models
from wagtail.snippets.models import register_snippet

from cms.private_media.models.images import PrivateMediaMixin


if TYPE_CHECKING:
    from django.db.models.fields.files import FieldFile


@register_snippet
class Chart(PrivateMediaMixin, models.Model):
    ...
    thumbnail_image = models.ImageField()
    data_csv = models.FileField()

    def get_privacy_controlled_files(self) -> Iterator["FieldFile"]:
        """Return an iterator of the files that should be protected."""
        yield self.thumbnail_image, yield self.data_csv
```

Depending on the type of model, it might also be necessary to [register the model with Wagtail's reference index](https://docs.wagtail.org/en/v6.3.1/advanced_topics/reference_index.html) (Though, this shouldn't be neccessary for snippets).

The default model manager inherited from `PrivateMediaMixin` implements all of the methods required for keeping privacy up-to-date, and the existing signal handlers that listen for content changes will start looking for references to your model instances, and trigger privacy updates accordingly.
