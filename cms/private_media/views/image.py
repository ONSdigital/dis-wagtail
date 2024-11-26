from wagtail.images import get_image_model
from wagtail.images.views.chooser import viewset as chooser_viewset
from wagtail.images.views.chooser import ImageChooseView as WagtailImageChooseView


from cms.private_media.views.mixins import ParentIdentifyingChooserViewMixin


class ImageChooseView(ParentIdentifyingChooserViewMixin, WagtailImageChooseView):
    """A replacement for Wagtail's ImageChooseView that identifies the
    'parent object' from the 'parent_url' query parameter, and uses it
    to populate hidden field values in the 'creation' form.
    """
    @classmethod
    def as_view(cls, **kwargs):
        _kwargs = chooser_viewset.get_common_view_kwargs()
        _kwargs.update(kwargs)
        _kwargs.pop("per_page")
        return super().as_view(**_kwargs)
