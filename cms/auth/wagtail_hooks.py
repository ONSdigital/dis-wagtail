from django.conf import settings
from django.utils.html import format_html
from django.utils.safestring import SafeString, mark_safe
from django_jinja.builtins.filters import static
from wagtail import hooks

from cms.auth.utils import get_auth_config


def register_global_admin_auth_js_hook() -> None:
    """Conditionally register the global admin Auth JS hook based on an whether Cognito login is enabled."""
    if not settings.AWS_COGNITO_LOGIN_ENABLED:
        return

    @hooks.register("insert_global_admin_js")
    def global_admin_auth_js() -> SafeString:
        """Register the auth.js script in the Wagtail admin to handle refresh logic."""
        return format_html(
            """
            <script>
                window.authConfig = {config};
            </script>
            <script src="{auth_js_path}"></script>
            """,
            config=mark_safe(get_auth_config()),  # noqa: S308
            auth_js_path=static("js/auth.js"),
        )


register_global_admin_auth_js_hook()
