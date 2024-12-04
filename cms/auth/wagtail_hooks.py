from django.conf import settings
from django.utils.html import format_html
from django.utils.safestring import SafeString
from django_jinja.builtins.filters import static
from wagtail import hooks


@hooks.register("insert_global_admin_js")
def global_admin_js() -> SafeString:
    """Register the auth.js script in the Wagtail admin to handle refresh logic."""
    auth_token_refresh_url = settings.AUTH_TOKEN_REFRESH_URL
    wagtail_admin_home_path = settings.WAGTAILADMIN_HOME_PATH
    csrf_cookie_name = settings.CSRF_COOKIE_NAME
    # Default value for csrf_header_name is "HTTP_X_CSRFTOKEN", the header needs to be set as "X-CSRFToken"
    # Django will convert the header to "HTTP_X_CSRFTOKEN" when it is received
    # @see: https://docs.djangoproject.com/en/5.1/ref/settings/#csrf-header-name
    csrf_header_name = settings.CSRF_HEADER_NAME.replace("HTTP_", "").replace("_", "-")
    logout_redirect_url = settings.LOGOUT_REDIRECT_URL
    auth_js_path = static("js/auth.js")

    script_template = """
            <script>
                window.authTokenRefreshUrl = "{auth_token_refresh_url}";
                window.wagtailAdminHomePath = "{wagtail_admin_home_path}";
                window.csrfCookieName = "{csrf_cookie_name}";
                window.csrfHeaderName = "{csrf_header_name}";
                window.logoutRedirectUrl = "{logout_redirect_url}";
            </script>
            <script src="{auth_js_path}"></script>
        """
    return format_html(
        script_template,
        auth_token_refresh_url=auth_token_refresh_url,
        wagtail_admin_home_path=wagtail_admin_home_path,
        csrf_cookie_name=csrf_cookie_name,
        csrf_header_name=csrf_header_name,
        logout_redirect_url=logout_redirect_url,
        auth_js_path=auth_js_path,
    )
