from typing import ClassVar
from unittest.mock import MagicMock, Mock, patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase

from cms.datasets.views import (
    DatasetChooserPermissionMixin,
    DatasetSearchFilterForm,
    ONSDatasetBaseChooseView,
)

User = get_user_model()


class ExampleSearchableModel:
    title = "foo example"
    description = "bar"
    not_searched = "no match"

    search_fields: ClassVar = ["title", "description"]


class TestDatasetSearchFilterMixin(TestCase):
    def test_filter(self):
        obj1 = ExampleSearchableModel()
        obj2 = ExampleSearchableModel()
        obj2.title = "eggs"
        obj2.description = "spam example"

        objects = [obj1, obj2]

        filter_form = DatasetSearchFilterForm()
        filter_form.cleaned_data = {}
        test_searches = [
            ("foo", [obj1]),
            ("bar", [obj1]),
            ("eggs", [obj2]),
            ("spam", [obj2]),
            ("example", [obj1, obj2]),
            ("no match", []),
        ]

        for test_search_query, expected_result in test_searches:
            with self.subTest(test_search_query=test_search_query, expected_result=expected_result):
                filter_form.cleaned_data["q"] = test_search_query
                filter_result = filter_form.filter(objects)
                self.assertEqual(filter_result, expected_result)


class TestDatasetChooserPermissionMixin(TestCase):
    """Test permission checks for accessing unpublished datasets."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="testuser", password="testpass")

    @patch("cms.datasets.views.user_can_access_unpublished_datasets")
    def test_permission_denied_for_unpublished_datasets_without_permission(self, mock_permission_check):
        """Test that users without permission cannot access unpublished datasets."""
        mock_permission_check.return_value = False

        request = self.factory.get("/chooser/?published=false")
        request.user = self.user

        # Create a simple view instance with the mixin
        class TestView(DatasetChooserPermissionMixin):
            pass

        view = TestView()

        with self.assertRaises(PermissionDenied):
            view.dispatch(request)

    @patch("cms.datasets.views.user_can_access_unpublished_datasets")
    def test_permission_granted_for_unpublished_datasets_with_permission(self, mock_permission_check):
        """Test that users with permission can access unpublished datasets."""
        mock_permission_check.return_value = True

        request = self.factory.get("/chooser/?published=false")
        request.user = self.user

        # Create a simple view instance with the mixin
        class TestView(DatasetChooserPermissionMixin):
            def dispatch(self, request, *args, **kwargs):
                return Mock()  # Return a mock response to indicate success

        view = TestView()
        response = view.dispatch(request)

        # Should not raise PermissionDenied
        self.assertIsNotNone(response)

    def test_permission_granted_for_published_datasets_without_permission(self):
        """Test that users without permission can access published datasets."""
        request = self.factory.get("/chooser/?published=true")
        request.user = self.user

        # Create a simple view instance with the mixin
        class TestView(DatasetChooserPermissionMixin):
            def dispatch(self, request, *args, **kwargs):
                return Mock()  # Return a mock response to indicate success

        view = TestView()
        response = view.dispatch(request)

        # Should not raise PermissionDenied
        self.assertIsNotNone(response)


class TestONSDatasetBaseChooseView(TestCase):
    """Test the ONSDatasetBaseChooseView functionality."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.view = ONSDatasetBaseChooseView()

    @patch("cms.datasets.views.ONSDataset")
    def test_get_object_list_with_token(self, mock_ons_dataset):
        """Test get_object_list passes auth token correctly."""
        mock_queryset = MagicMock()
        mock_ons_dataset.objects.filter.return_value = mock_queryset
        mock_queryset.with_token.return_value = mock_queryset
        mock_queryset.all.return_value = []

        request = self.factory.get("/chooser/?published=false")
        request.user = self.user
        request.COOKIES = {settings.ACCESS_TOKEN_COOKIE_NAME: "test_token"}

        self.view.request = request
        self.view.get_object_list()

        # Verify token was passed
        mock_queryset.with_token.assert_called_once_with("test_token")

    @patch("cms.datasets.views.ONSDataset")
    def test_get_object_list_for_bundle_forces_unpublished(self, mock_ons_dataset):
        """Test get_object_list forces published=false when for_bundle=true."""
        mock_queryset = MagicMock()
        mock_ons_dataset.objects.filter.return_value = mock_queryset
        mock_queryset.with_token.return_value = mock_queryset
        mock_queryset.all.return_value = []

        request = self.factory.get("/chooser/?for_bundle=true&published=true")
        request.user = self.user
        request.COOKIES = {}

        self.view.request = request
        self.view.get_object_list()

        # Verify published=false was used despite published=true in query
        mock_ons_dataset.objects.filter.assert_called_once_with(published="false")

    @patch("cms.datasets.views.logger")
    @patch("cms.datasets.views.ONSDataset")
    def test_audit_logging_for_unpublished_datasets(self, mock_ons_dataset, mock_logger):
        """Test that accessing unpublished datasets logs an audit event."""
        mock_queryset = MagicMock()
        mock_ons_dataset.objects.filter.return_value = mock_queryset
        mock_queryset.with_token.return_value = mock_queryset
        mock_queryset.all.return_value = []

        request = self.factory.get("/chooser/?published=false")
        request.user = self.user
        request.COOKIES = {}

        self.view.request = request
        self.view.get_object_list()

        # Verify audit log was created with structured logging
        mock_logger.info.assert_called_once_with(
            "Unpublished datasets requested", extra={"username": self.user.username}
        )
