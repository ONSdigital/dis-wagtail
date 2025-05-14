from django.urls import reverse
from wagtail.test.utils import WagtailPageTestCase


class BundlesPageTest(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = cls.create_superuser("admin")

    def test_date_placeholder(self):
        """Test that the date input field displays date placeholder."""
        self.client.force_login(self.user)

        add_bundles_url = reverse("bundle:add")
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
