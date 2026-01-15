from wagtail_factories import ImageFactory as BaseImageFactory


class ImageFactory(BaseImageFactory):
    class Meta:
        model = BaseImageFactory._meta.model
        django_get_or_create = ("title",)
