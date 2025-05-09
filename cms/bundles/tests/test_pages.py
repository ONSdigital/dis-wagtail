from django.urls import reverse
from wagtail.test.utils import WagtailPageTestCase

from cms.bundles.tests.factories import BundlePageFactory


class BundlesPageTest(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.page = BundlePageFactory()
        cls.user = cls.create_superuser("admin")

    def test_date_placeholder(self):
        """Test that the date input field displays date placeholder."""
        self.client.force_login(self.user)

        add_bundles_url = reverse("wagtailadmin_pages:add", args=["bundle", "new"])

        response = self.client.get(add_bundles_url, follow=True)

        content = response.content.decode(encoding="utf-8")

        datetime_placeholder = "YYYY-MM-DD HH:MM"

        self.assertInHTML(
            (
                '<input type="text" name="publication_date" autocomplete="off"'
                f'placeholder="{datetime_placeholder}" id="id_publication_date">'
            ),
            content,
        )
        self.assertInHTML(
            (
                '<input type="text" name="last_revised_date" autocomplete="off"'
                f' placeholder="{datetime_placeholder}" id="id_last_revised_date">'
            ),
            content,
        )
