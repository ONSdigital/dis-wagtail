import factory
from wagtail.models import Collection
from wagtail_factories import ImageFactory as BaseImageFactory


class ImageFactory(BaseImageFactory):
    """A modified ImageFactory which uses title as a unique identifier."""

    collection = factory.LazyFunction(Collection.get_first_root_node)  # ignore[no-untyped-call]

    class Meta:
        model = BaseImageFactory._meta.model
        django_get_or_create = ("title",)
