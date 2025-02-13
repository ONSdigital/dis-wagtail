from behave import given
from behave.runner import Context

from cms.themes.tests.factories import ThemePageFactory


@given("a theme page exists")
def a_theme_page_already_exists(context: Context):
    context.theme_page = ThemePageFactory()
