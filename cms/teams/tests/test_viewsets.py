from http import HTTPStatus

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.formats import date_format
from wagtail.test.utils import WagtailTestUtils

from cms.core.tests.utils import rebuild_internal_search_index
from cms.teams.models import Team
from cms.teams.tests.factories import TeamFactory
from cms.teams.viewsets import team_chooser_viewset


class TeamsViewSetTestCase(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="publishing_admin")
        cls.active_team = TeamFactory(name="Statistics Team", identifier="stats-team", is_active=True)
        cls.inactive_team = TeamFactory(name="Research Team", identifier="research-team", is_active=False)
        cls.another_active_team = TeamFactory(name="Data Team", identifier="data-team", is_active=True)

        cls.teams_index_url = reverse("teams:index")
        cls.teams_add_url = reverse("teams:add")
        cls.team_edit_url = reverse("teams:edit", args=[cls.active_team.pk])
        cls.team_delete_url = reverse("teams:delete", args=[cls.active_team.pk])
        cls.team_inspect_url = reverse("teams:inspect", args=[cls.active_team.pk])
        cls.chooser_url = reverse(team_chooser_viewset.get_url_name("choose"))
        cls.chooser_results_url = reverse(team_chooser_viewset.get_url_name("choose_results"))

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_teams_index_view_shows_only_active_teams(self):
        response = self.client.get(self.teams_index_url)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, self.active_team.name)
        self.assertContains(response, self.another_active_team.name)
        self.assertContains(response, self.active_team.identifier)
        self.assertContains(response, self.another_active_team.identifier)
        self.assertNotContains(response, self.inactive_team.name)
        self.assertNotContains(response, self.inactive_team.identifier)

    def test_chooser_viewset_shows_only_active_teams(self):
        response = self.client.get(self.chooser_url)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, "Name")
        self.assertContains(response, "Identifier")
        self.assertContains(response, "Last Updated")
        self.assertContains(response, self.active_team.name)
        self.assertContains(response, self.active_team.identifier)
        self.assertContains(response, self.another_active_team.name)
        self.assertContains(response, self.another_active_team.identifier)
        self.assertNotContains(response, self.inactive_team.name)
        self.assertNotContains(response, self.inactive_team.identifier)

    def test_chooser_search_active_team_found(self):
        rebuild_internal_search_index()
        response = self.client.get(f"{self.chooser_results_url}?q=statistics")

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, self.active_team.name)
        self.assertNotContains(response, self.another_active_team.name)
        self.assertNotContains(response, self.inactive_team.name)

    def test_chooser_search_inactive_team_not_found(self):
        rebuild_internal_search_index()
        response = self.client.get(f"{self.chooser_results_url}?q=research")

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertNotContains(response, self.inactive_team.name)
        self.assertContains(response, 'Sorry, there are no matches for "<em>research</em>"', html=True)

    def test_chooser_search_data_team_found(self):
        rebuild_internal_search_index()
        response = self.client.get(f"{self.chooser_results_url}?q=data")

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, self.another_active_team.name)
        self.assertNotContains(response, self.active_team.name)
        self.assertNotContains(response, self.inactive_team.name)

    def test_chooser_no_results(self):
        response = self.client.get(f"{self.chooser_results_url}?q=nonexistent")
        self.assertContains(response, 'Sorry, there are no matches for "<em>nonexistent</em>"', html=True)

    def test_inspect_viewset(self):
        self.active_team.users.add(self.superuser)
        response = self.client.get(self.team_inspect_url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, self.active_team.name)
        self.assertContains(response, "Identifier")
        self.assertContains(response, self.active_team.identifier)
        self.assertContains(response, "Is active")
        self.assertContains(response, "True")
        self.assertContains(response, "Created at")
        self.assertContains(response, date_format(self.active_team.created_at))
        self.assertContains(response, "Updated at")
        self.assertContains(response, date_format(self.active_team.updated_at))
        self.assertContains(response, "Users")
        self.assertContains(response, self.superuser.username, 2)  # one for the account, one in the content

    def test_add_view__with_team_management_disabled(self):
        response = self.client.get(self.teams_add_url, follow=True)
        self.assertRedirects(response, "/admin/")
        self.assertContains(response, "Sorry, you do not have permission to access this area.")

    def test_edit_view__with_team_management_disabled(self):
        response = self.client.get(self.team_edit_url, follow=True)
        self.assertRedirects(response, "/admin/")
        self.assertContains(response, "Sorry, you do not have permission to access this area.")

    def test_delete_view__with_team_management_disabled(self):
        response = self.client.get(self.team_delete_url, follow=True)
        self.assertRedirects(response, "/admin/")
        self.assertContains(response, "Sorry, you do not have permission to access this area.")

    @override_settings(ALLOW_TEAM_MANAGEMENT=True)
    def test_add_view__with_team_management_enabled(self):
        self.assertEqual(Team.objects.count(), 3)
        response = self.client.get(self.teams_add_url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, "New: Team")

        response = self.client.post(self.teams_add_url, {"name": "New Team", "identifier": "new-team"})
        self.assertRedirects(response, self.teams_index_url)

        self.assertEqual(Team.objects.count(), 4)

    @override_settings(ALLOW_TEAM_MANAGEMENT=True)
    def test_edit_view__with_team_management_enabled(self):
        response = self.client.get(self.team_edit_url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, f"Editing: {self.active_team.name}")

        response = self.client.post(
            self.team_edit_url, {"name": "Updated Team", "identifier": self.active_team.identifier}
        )
        self.assertRedirects(response, self.teams_index_url)

        self.active_team.refresh_from_db()
        self.assertEqual(self.active_team.name, "Updated Team")

    @override_settings(ALLOW_TEAM_MANAGEMENT=True)
    def test_delete_view__with_team_management_enabled(self):
        self.assertEqual(Team.objects.count(), 3)
        response = self.client.get(self.team_delete_url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, "Are you sure you want to delete this team?")

        response = self.client.post(self.team_delete_url)
        self.assertRedirects(response, self.teams_index_url)
        self.assertEqual(Team.objects.count(), 2)


class TeamModelTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.active_team = TeamFactory(name="Active Team", identifier="active-team", is_active=True)
        cls.inactive_team = TeamFactory(name="Inactive Team", identifier="inactive-team", is_active=False)

    def test_team_objects_active_queryset_method(self):
        """Test that Team.objects.active() returns only active teams."""
        active_teams = Team.objects.active()

        self.assertIn(self.active_team, active_teams)
        self.assertNotIn(self.inactive_team, active_teams)
        self.assertEqual(active_teams.count(), 1)

    def test_team_queryset_active_method_chaining(self):
        """Test that active() method can be chained with other queryset methods."""
        active_teams_filtered = Team.objects.filter(name__icontains="active").active()

        self.assertIn(self.active_team, active_teams_filtered)
        self.assertNotIn(self.inactive_team, active_teams_filtered)
        self.assertEqual(active_teams_filtered.count(), 1)

    def test_team_queryset_active_method_with_no_active_teams(self):
        """Test that active() method returns empty queryset when no teams are active."""
        Team.objects.filter(is_active=True).update(is_active=False)

        active_teams = Team.objects.active()
        self.assertEqual(active_teams.count(), 0)
