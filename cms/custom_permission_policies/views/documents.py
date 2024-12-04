from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from wagtail.documents.views.chooser import DocumentChooseView as WagtailDocumentChooseView
from wagtail.documents.views.chooser import viewset as chooser_viewset

from .mixins import ParentIdentifyingChooserViewMixin

if TYPE_CHECKING:
    from django.http import HttpResponse


class DocumentChooseView(ParentIdentifyingChooserViewMixin, WagtailDocumentChooseView):
    """A replacement for Wagtail's DocumentChooseView that identifies the
    'parent object' from the 'parent_url' query parameter, and uses it
    to populate hidden field values in the 'creation' form.
    """

    @classmethod
    def as_view(cls, **kwargs: Any) -> Callable[..., "HttpResponse"]:
        """Wagtail's version of this view is modified quite heavily by the "DocumentChooserViewSet"
        instance before it is actually registered. This override mimics some of that by retreiving
        some of those overrides from the viewset instance and applying them here.
        """
        _kwargs = chooser_viewset.get_common_view_kwargs()
        _kwargs.update(kwargs)
        _kwargs.pop("per_page")
        view: Callable[..., HttpResponse] = super().as_view(**_kwargs)
        return view
