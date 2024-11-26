from wagtail.documents.views.chooser import viewset as chooser_viewset
from wagtail.documents.views.chooser import DocumentChooseView as WagtailDocumentChooseView

from cms.private_media.views.mixins import ParentIdentifyingChooserViewMixin


class DocumentChooseView(ParentIdentifyingChooserViewMixin, WagtailDocumentChooseView):
    """A replacement for Wagtail's DocumentChooseView that identifies the
    'parent object' from the 'parent_url' query parameter, and uses it
    to populate hidden field values in the 'creation' form.
    """
    @classmethod
    def as_view(cls, **kwargs):
        _kwargs = chooser_viewset.get_common_view_kwargs()
        _kwargs.update(kwargs)
        _kwargs.pop("per_page")
        return super().as_view(**_kwargs)
