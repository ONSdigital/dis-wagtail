from wagtail_factories import ImageFactory as BaseImageFactory


class ImageFactory(BaseImageFactory):
    """A modified ImageFactory which uses title as a unique identifier."""

    class Meta:
        model = BaseImageFactory._meta.model
        django_get_or_create = ("title",)
