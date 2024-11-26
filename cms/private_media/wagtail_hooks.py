from django.templatetags.static import static
from django.utils.html import format_html
from wagtail import hooks


@hooks.register("insert_editor_js")
def load_chooser_modal_override_js():
    return format_html(
        """
        <script src="{0}"></script>
        """,
        static("private_media/js/chooser-modal-overrides.js"),
    )
