from django.urls import reverse
from wagtail.test.utils import WagtailPageTestCase

from cms.standard_pages.tests.factories import InformationPageFactory


class DatePlaceholderTestCase(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.page = InformationPageFactory()
        cls.user = cls.create_superuser("admin")

    def test_date_placeholder(self):
        """Test that the date input field displays date placeholder."""
        self.client.force_login(self.user)

        parent_page = self.page.get_parent()

        add_sibling_url = reverse("wagtailadmin_pages:add", args=["standard_pages", "informationpage", parent_page.id])

        response = self.client.get(add_sibling_url, follow=True)

        content = response.content.decode(encoding="utf-8")

        date_placeholder = "YYYY-MM-DD"

        self.assertInHTML(
            f'<input type="text" name="last_updated" autocomplete="off" placeholder="{date_placeholder}" id="id_last_updated">',  # noqa: E501
            content,
        )
