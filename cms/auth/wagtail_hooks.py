from django.conf import settings
from django.utils.html import format_html, json_script
from django_jinja.builtins.filters import static
from wagtail import hooks

from cms.auth.utils import get_auth_config


def register_global_admin_auth_js_hook() -> None:
    """Conditionally register the global admin Auth JS hook based on an whether Cognito login is enabled."""
    if not settings.AWS_COGNITO_LOGIN_ENABLED:
        return

    @hooks.register("insert_global_admin_js")
    def global_admin_auth_js() -> str:
        """Insert a safe JSON payload and defer-loaded bundle into the Wagtail admin."""
        # Safely embed the auth configuration as a JSON data-island.
        config_tag: str = json_script(get_auth_config(), element_id="auth-config")

        # Add the Auth bundle; defer prevents render-blocking.
        return format_html(
            '{}<script src="{}" defer></script>',
            config_tag,
            static("js/auth.js"),
        )


register_global_admin_auth_js_hook()
