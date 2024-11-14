from typing import TYPE_CHECKING, Any, Union

from django.utils.html import format_html, format_html_join
from wagtail.admin.panels import HelpPanel, PageChooserPanel

if TYPE_CHECKING:
    from django.db.models import Model
    from django.utils.safestring import SafeString


class BundleNotePanel(HelpPanel):
    """An extended HelpPanel class."""

    class BoundPanel(HelpPanel.BoundPanel):
        def __init__(self, **kwargs: Any) -> None:
            super().__init__(**kwargs)
            self.content = self._content_for_instance(self.instance)

        def _content_for_instance(self, instance: "Model") -> Union[str, "SafeString"]:
            if not hasattr(instance, "bundles"):
                return ""

            if bundles := instance.bundles:
                content_html = format_html_join(
                    "\n",
                    "<li>{} (Status: {})</li>",
                    (
                        (
                            bundle.name,
                            bundle.get_status_display(),
                        )
                        for bundle in bundles
                    ),
                )

                content = format_html("<p>This page is in the following bundle(s):</p><ul>{}</ul>", content_html)
            else:
                content = format_html("<p>This page is not part of any bundles</p>")
            return content


class PageChooserWithStatusPanel(PageChooserPanel):
    """A custom page chooser panel that includes the page workflow status."""

    class BoundPanel(PageChooserPanel.BoundPanel):
        def __init__(self, **kwargs: Any) -> None:
            """Sets the panel heading to the page verbose name to help differentiate page types."""
            super().__init__(**kwargs)
            if page := self.instance.page:
                self.heading = page.specific.get_verbose_name()
