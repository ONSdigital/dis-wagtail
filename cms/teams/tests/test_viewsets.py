from django.test import TestCase
from django.urls import reverse
from wagtail.test.utils import WagtailTestUtils

from cms.teams.tests.factories import TeamFactory


class TeamsViewSetTestCase(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")
        cls.teams_index_url = reverse("teams:index")
        cls.team = TeamFactory(name="Statistics Team", identifier="stats-team")
        cls.another_team = TeamFactory(name="Research Team", identifier="research-team")

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_teams_index_view_shows_teams(self):
        response = self.client.get(self.teams_index_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.team.name)
        self.assertContains(response, self.another_team.name)
        self.assertContains(response, self.team.identifier)
        self.assertContains(response, self.another_team.identifier)
