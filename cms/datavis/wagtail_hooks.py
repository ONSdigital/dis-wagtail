from typing import TYPE_CHECKING

from django.templatetags.static import static
from django.utils.html import format_html
from wagtail import hooks
from wagtail.snippets.models import register_snippet

from cms.datavis.admin.views import DataVisViewSetGroup

if TYPE_CHECKING:
    from django.utils.safestring import SafeText

register_snippet(DataVisViewSetGroup)


@hooks.register("insert_editor_js")
def editor_js() -> "SafeText":
    return format_html('<script src="{}"></script>', static("admin/datavis/js/toggleDataSourceFields.js"))
