from django.test import TestCase
from django.urls import reverse
from wagtail.test.utils import WagtailTestUtils

from cms.teams.tests.factories import TeamFactory
from cms.teams.viewsets import team_chooser_viewset


class TeamsViewSetTestCase(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")
        cls.team = TeamFactory(name="Statistics Team", identifier="stats-team")
        cls.another_team = TeamFactory(name="Research Team", identifier="research-team")

        cls.teams_index_url = reverse("teams:index")
        cls.chooser_url = reverse(team_chooser_viewset.get_url_name("choose"))
        cls.chooser_results_url = reverse(team_chooser_viewset.get_url_name("choose_results"))

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_teams_index_view_shows_teams(self):
        response = self.client.get(self.teams_index_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.team.name)
        self.assertContains(response, self.another_team.name)
        self.assertContains(response, self.team.identifier)
        self.assertContains(response, self.another_team.identifier)

    def test_chooser_viewset(self):
        response = self.client.get(self.chooser_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Name")
        self.assertContains(response, "Identifier")
        self.assertContains(response, "Last Updated")
        self.assertContains(response, "Active?")
        self.assertContains(response, self.team.name)
        self.assertContains(response, self.team.identifier)
        self.assertContains(response, self.another_team.name)
        self.assertContains(response, self.another_team.identifier)

    def test_chooser_search(self):
        response = self.client.get(f"{self.chooser_results_url}?q=statistics")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.team.name)
        self.assertNotContains(response, self.another_team.name)

        response = self.client.get(f"{self.chooser_results_url}?q=research")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.another_team.name)
        self.assertNotContains(response, self.team.name)

    def test_chooser_no_results(self):
        response = self.client.get(f"{self.chooser_results_url}?q=nonexistent")
        self.assertContains(response, 'Sorry, there are no matches for "<em>nonexistent</em>"', html=True)
