# pylint: disable=too-many-lines

from typing import ClassVar
from unittest.mock import MagicMock, Mock, patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import DEFAULT_DB_ALIAS
from django.test import RequestFactory, TestCase

from cms.datasets.views import (
    DatasetChooserPermissionMixin,
    DatasetChosenMultipleViewMixin,
    DatasetChosenView,
    DatasetRetrievalMixin,
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


class TestDatasetRetrievalMixin(TestCase):
    """Test permission checks in DatasetRetrievalMixin.retrieve_dataset()."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="testuser", password="testpass")

        # Create a test view instance with the mixin
        class TestView(DatasetRetrievalMixin):
            def __init__(self):
                self.request = None

        self.view = TestView()

    @patch("cms.datasets.views.user_can_access_unpublished_datasets")
    @patch("cms.datasets.views.ONSDataset")
    def test_retrieve_unpublished_dataset_without_permission_raises_error(
        self, mock_ons_dataset, mock_permission_check
    ):
        """Test that retrieving unpublished datasets without permission raises PermissionDenied."""
        mock_permission_check.return_value = False

        request = self.factory.get("/chooser/")
        request.user = self.user
        self.view.request = request

        with self.assertRaises(PermissionDenied):
            self.view.retrieve_dataset(dataset_id="dataset-123", published=False, access_token=None)

        # Verify permission check was called
        mock_permission_check.assert_called_once_with(self.user)
        # Verify API was not called since permission was denied
        mock_ons_dataset.objects.get.assert_not_called()

    @patch("cms.datasets.views.user_can_access_unpublished_datasets")
    @patch("cms.datasets.views.get_dataset_for_published_state")
    @patch("cms.datasets.views.ONSDataset")
    def test_retrieve_unpublished_dataset_with_permission_succeeds(
        self, mock_ons_dataset, mock_get_dataset, mock_permission_check
    ):
        """Test that retrieving unpublished datasets with permission succeeds."""
        mock_permission_check.return_value = True

        mock_api_dataset = Mock()
        mock_api_dataset.title = "Test Dataset"
        mock_queryset = MagicMock()
        mock_ons_dataset.objects = mock_queryset
        mock_queryset.get.return_value = mock_api_dataset

        mock_get_dataset.return_value = {"title": "Test Dataset"}

        request = self.factory.get("/chooser/")
        request.user = self.user
        self.view.request = request

        result = self.view.retrieve_dataset(dataset_id="dataset-123", published=False, access_token=None)

        # Verify permission check was called
        mock_permission_check.assert_called_once_with(self.user)
        # Verify API was called
        mock_queryset.get.assert_called_once_with(pk="dataset-123")
        # Verify result was returned
        self.assertEqual(result, {"title": "Test Dataset"})

    @patch("cms.datasets.views.get_dataset_for_published_state")
    @patch("cms.datasets.views.ONSDataset")
    def test_retrieve_published_dataset_without_permission_check(self, mock_ons_dataset, mock_get_dataset):
        """Test that retrieving published datasets does not require permission check."""
        mock_api_dataset = Mock()
        mock_api_dataset.title = "Test Dataset"
        mock_queryset = MagicMock()
        mock_ons_dataset.objects = mock_queryset
        mock_queryset.get.return_value = mock_api_dataset

        mock_get_dataset.return_value = {"title": "Test Dataset"}

        request = self.factory.get("/chooser/")
        request.user = self.user
        self.view.request = request

        result = self.view.retrieve_dataset(dataset_id="dataset-123", published=True, access_token=None)

        # Verify API was called
        mock_queryset.get.assert_called_once_with(pk="dataset-123")
        # Verify result was returned
        self.assertEqual(result, {"title": "Test Dataset"})

    @patch("cms.datasets.views.user_can_access_unpublished_datasets")
    @patch("cms.datasets.views.get_dataset_for_published_state")
    @patch("cms.datasets.views.ONSDataset")
    def test_retrieve_dataset_with_access_token(self, mock_ons_dataset, mock_get_dataset, mock_permission_check):
        """Test that retrieve_dataset passes access token to API queryset."""
        mock_permission_check.return_value = True

        mock_api_dataset = Mock()
        mock_api_dataset.title = "Test Dataset"
        mock_queryset = MagicMock()
        mock_ons_dataset.objects = mock_queryset
        mock_queryset.with_token.return_value = mock_queryset
        mock_queryset.get.return_value = mock_api_dataset

        mock_get_dataset.return_value = {"title": "Test Dataset"}

        request = self.factory.get("/chooser/")
        request.user = self.user
        self.view.request = request

        self.view.retrieve_dataset(dataset_id="dataset-123", published=False, access_token="test_token")

        # Verify token was passed
        mock_queryset.with_token.assert_called_once_with("test_token")
        mock_queryset.get.assert_called_once_with(pk="dataset-123")


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


class TestDatasetChosenView(TestCase):
    """Test the DatasetChosenView functionality."""

    def setUp(self):
        self.factory = RequestFactory()
        # Create a user for the request
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.view = DatasetChosenView()

    @patch("cms.datasets.views.user_can_access_unpublished_datasets")
    @patch("cms.datasets.views.Dataset")
    def test_get_object_unpublished_without_permission_raises_error(self, mock_dataset, mock_permission_check):
        """Test that get_object raises PermissionDenied for unpublished datasets without permission."""
        mock_permission_check.return_value = False

        request = self.factory.get("/chooser/")
        request.user = self.user
        request.COOKIES = {}

        self.view.request = request

        with self.assertRaises(PermissionDenied):
            self.view.get_object("dataset-123,2021,1,false")

        # Verify permission check was called
        mock_permission_check.assert_called_once_with(self.user)
        # Verify Dataset was not created since permission was denied
        mock_dataset.objects.get_or_create.assert_not_called()

    @patch("cms.datasets.views.user_can_access_unpublished_datasets")
    @patch("cms.datasets.views.get_dataset_for_published_state")
    @patch("cms.datasets.views.Dataset")
    @patch("cms.datasets.views.ONSDataset")
    def test_get_object_unpublished_with_permission_succeeds(
        self, mock_ons_dataset, mock_dataset, mock_get_dataset, mock_permission_check
    ):
        """Test that get_object succeeds for unpublished datasets with permission."""
        mock_permission_check.return_value = True

        # Mock the API dataset
        mock_api_dataset = Mock()
        mock_api_dataset.title = "Test Dataset"
        mock_api_dataset.description = "Test Description"

        mock_queryset = MagicMock()
        mock_ons_dataset.objects = mock_queryset
        mock_queryset.get.return_value = mock_api_dataset

        mock_get_dataset.return_value = mock_api_dataset

        # Mock the Django Dataset model
        mock_dataset_instance = Mock()
        mock_dataset.objects.get_or_create.return_value = (mock_dataset_instance, True)

        request = self.factory.get("/chooser/")
        request.user = self.user
        request.COOKIES = {}

        self.view.request = request
        result = self.view.get_object("dataset-123,2021,1,false")

        # Verify permission check was called
        mock_permission_check.assert_called_once_with(self.user)
        # Verify Dataset was created
        mock_dataset.objects.get_or_create.assert_called_once()
        self.assertEqual(result, mock_dataset_instance)

    @patch("cms.datasets.views.get_dataset_for_published_state")
    @patch("cms.datasets.views.Dataset")
    @patch("cms.datasets.views.ONSDataset")
    def test_get_object_published_without_permission_check(self, mock_ons_dataset, mock_dataset, mock_get_dataset):
        """Test that get_object for published datasets does not require permission check."""
        # Mock the API dataset
        mock_api_dataset = Mock()
        mock_api_dataset.title = "Test Dataset"
        mock_api_dataset.description = "Test Description"

        mock_queryset = MagicMock()
        mock_ons_dataset.objects = mock_queryset
        mock_queryset.get.return_value = mock_api_dataset

        mock_get_dataset.return_value = mock_api_dataset

        # Mock the Django Dataset model
        mock_dataset_instance = Mock()
        mock_dataset.objects.get_or_create.return_value = (mock_dataset_instance, True)

        request = self.factory.get("/chooser/")
        request.user = self.user
        request.COOKIES = {}

        self.view.request = request
        result = self.view.get_object("dataset-123,2021,1,true")

        # Verify Dataset was created
        mock_dataset.objects.get_or_create.assert_called_once()
        self.assertEqual(result, mock_dataset_instance)

    @patch("cms.datasets.views.get_dataset_for_published_state")
    @patch("cms.datasets.views.Dataset")
    @patch("cms.datasets.views.ONSDataset")
    def test_get_object_with_token(self, mock_ons_dataset, mock_dataset, mock_get_dataset):
        """Test get_object passes auth token when fetching dataset from API."""
        # Mock the API dataset
        mock_api_dataset = Mock()
        mock_api_dataset.title = "Test Dataset"
        mock_api_dataset.description = "Test Description"

        mock_queryset = MagicMock()
        mock_ons_dataset.objects = mock_queryset
        mock_queryset.with_token.return_value = mock_queryset
        mock_queryset.get.return_value = mock_api_dataset

        mock_get_dataset.return_value = mock_api_dataset

        # Mock the Django Dataset model
        mock_dataset_instance = Mock()
        mock_dataset.objects.get_or_create.return_value = (mock_dataset_instance, True)

        request = self.factory.get("/chooser/")
        request.user = self.user
        request.COOKIES = {settings.ACCESS_TOKEN_COOKIE_NAME: "test_token"}

        self.view.request = request
        self.view.get_object("dataset-123,2021,1,true")

        # Verify token was passed
        mock_queryset.with_token.assert_called_once_with("test_token")
        mock_queryset.get.assert_called_once_with(pk="dataset-123")

    @patch("cms.datasets.views.get_dataset_for_published_state")
    @patch("cms.datasets.views.Dataset")
    @patch("cms.datasets.views.ONSDataset")
    def test_get_object_without_token(self, mock_ons_dataset, mock_dataset, mock_get_dataset):
        """Test get_object works without auth token."""
        # Mock the API dataset
        mock_api_dataset = Mock()
        mock_api_dataset.title = "Test Dataset"
        mock_api_dataset.description = "Test Description"

        mock_queryset = MagicMock()
        mock_ons_dataset.objects = mock_queryset
        mock_queryset.get.return_value = mock_api_dataset

        mock_get_dataset.return_value = mock_api_dataset

        # Mock the Django Dataset model
        mock_dataset_instance = Mock()
        mock_dataset.objects.get_or_create.return_value = (mock_dataset_instance, True)

        request = self.factory.get("/chooser/")
        request.user = self.user
        request.COOKIES = {}

        self.view.request = request
        self.view.get_object("dataset-123,2021,1,true")

        # Verify with_token was NOT called
        mock_queryset.with_token.assert_not_called()
        mock_queryset.get.assert_called_once_with(pk="dataset-123")

    @patch("cms.datasets.views.get_dataset_for_published_state")
    @patch("cms.datasets.views.Dataset")
    @patch("cms.datasets.views.ONSDataset")
    def test_get_object_updates_existing_dataset_with_changed_metadata(
        self, mock_ons_dataset, mock_dataset, mock_get_dataset
    ):
        """Test that existing datasets get updated when API metadata changes."""
        # Mock the API dataset with new metadata
        mock_api_dataset = Mock()
        mock_api_dataset.title = "Updated Title"
        mock_api_dataset.description = "Updated Description"

        mock_queryset = MagicMock()
        mock_ons_dataset.objects = mock_queryset
        mock_queryset.get.return_value = mock_api_dataset

        mock_get_dataset.return_value = mock_api_dataset

        # Mock existing dataset with old metadata
        mock_dataset_instance = Mock()
        mock_dataset_instance.title = "Old Title"
        mock_dataset_instance.description = "Old Description"
        # (existing dataset, created False)
        mock_dataset.objects.get_or_create.return_value = (mock_dataset_instance, False)

        request = self.factory.get("/chooser/")
        request.user = self.user
        request.COOKIES = {}

        self.view.request = request
        result = self.view.get_object("dataset-123,2021,1,true")

        # Verify dataset was fetched (not created)
        mock_dataset.objects.get_or_create.assert_called_once_with(
            namespace="dataset-123",
            edition="2021",
            version=1,
            defaults={"title": "Updated Title", "description": "Updated Description"},
        )

        # Verify metadata was updated
        self.assertEqual(mock_dataset_instance.title, "Updated Title")
        self.assertEqual(mock_dataset_instance.description, "Updated Description")

        # Verify save was called with updated fields
        mock_dataset_instance.save.assert_called_once()
        call_args = mock_dataset_instance.save.call_args
        self.assertEqual(set(call_args.kwargs["update_fields"]), {"title", "description"})
        self.assertEqual(result, mock_dataset_instance)

    @patch("cms.datasets.views.get_dataset_for_published_state")
    @patch("cms.datasets.views.Dataset")
    @patch("cms.datasets.views.ONSDataset")
    def test_get_object_skips_save_when_metadata_unchanged(self, mock_ons_dataset, mock_dataset, mock_get_dataset):
        """Test that save is skipped when existing metadata matches API data."""
        # Mock the API dataset
        mock_api_dataset = Mock()
        mock_api_dataset.title = "Same Title"
        mock_api_dataset.description = "Same Description"

        mock_queryset = MagicMock()
        mock_ons_dataset.objects = mock_queryset
        mock_queryset.get.return_value = mock_api_dataset

        mock_get_dataset.return_value = mock_api_dataset

        # Mock existing dataset with same metadata
        mock_dataset_instance = Mock()
        mock_dataset_instance.title = "Same Title"
        mock_dataset_instance.description = "Same Description"
        # (existing dataset, created False)
        mock_dataset.objects.get_or_create.return_value = (mock_dataset_instance, False)

        request = self.factory.get("/chooser/")
        request.user = self.user
        request.COOKIES = {}

        self.view.request = request
        result = self.view.get_object("dataset-123,2021,1,true")

        # Verify save was NOT called since metadata hasn't changed
        mock_dataset_instance.save.assert_not_called()
        self.assertEqual(result, mock_dataset_instance)

    @patch("cms.datasets.views.get_dataset_for_published_state")
    @patch("cms.datasets.views.Dataset")
    @patch("cms.datasets.views.ONSDataset")
    def test_get_object_updates_only_changed_field(self, mock_ons_dataset, mock_dataset, mock_get_dataset):
        """Test that only changed fields are included in save."""
        # Mock the API dataset with one field changed
        mock_api_dataset = Mock()
        mock_api_dataset.title = "New Title"
        mock_api_dataset.description = "Same Description"

        mock_queryset = MagicMock()
        mock_ons_dataset.objects = mock_queryset
        mock_queryset.get.return_value = mock_api_dataset

        mock_get_dataset.return_value = mock_api_dataset

        # Mock existing dataset
        mock_dataset_instance = Mock()
        mock_dataset_instance.title = "Old Title"
        mock_dataset_instance.description = "Same Description"
        # (existing dataset, created False)
        mock_dataset.objects.get_or_create.return_value = (mock_dataset_instance, False)

        request = self.factory.get("/chooser/")
        request.user = self.user
        request.COOKIES = {}

        self.view.request = request
        self.view.get_object("dataset-123,2021,1,true")

        # Verify only title was updated
        self.assertEqual(mock_dataset_instance.title, "New Title")
        self.assertEqual(mock_dataset_instance.description, "Same Description")

        # Verify save was called with only title in update_fields
        mock_dataset_instance.save.assert_called_once_with(update_fields=["title"])

    @patch("cms.datasets.views.get_dataset_for_published_state")
    @patch("cms.datasets.views.Dataset")
    @patch("cms.datasets.views.ONSDataset")
    def test_get_object_creates_new_dataset_without_update(self, mock_ons_dataset, mock_dataset, mock_get_dataset):
        """Test that newly created datasets don't trigger update logic."""
        # Mock the API dataset
        mock_api_dataset = Mock()
        mock_api_dataset.title = "New Dataset"
        mock_api_dataset.description = "New Description"

        mock_queryset = MagicMock()
        mock_ons_dataset.objects = mock_queryset
        mock_queryset.get.return_value = mock_api_dataset

        mock_get_dataset.return_value = mock_api_dataset

        # Mock newly created dataset
        mock_dataset_instance = Mock()
        mock_dataset.objects.get_or_create.return_value = (mock_dataset_instance, True)

        request = self.factory.get("/chooser/")
        request.user = self.user
        request.COOKIES = {}

        self.view.request = request
        result = self.view.get_object("dataset-123,2021,1,true")

        # Verify save was NOT called for newly created dataset
        mock_dataset_instance.save.assert_not_called()
        self.assertEqual(result, mock_dataset_instance)

    @patch("cms.datasets.views.get_dataset_for_published_state")
    @patch("cms.datasets.views.Dataset")
    @patch("cms.datasets.views.ONSDataset")
    def test_get_object_skips_update_when_api_has_empty_values(self, mock_ons_dataset, mock_dataset, mock_get_dataset):
        """Test that empty/None values from API don't trigger updates."""
        # Mock the API dataset with empty values
        mock_api_dataset = Mock()
        mock_api_dataset.title = ""
        mock_api_dataset.description = None

        mock_queryset = MagicMock()
        mock_ons_dataset.objects = mock_queryset
        mock_queryset.get.return_value = mock_api_dataset

        mock_get_dataset.return_value = mock_api_dataset

        # Mock existing dataset with valid values
        mock_dataset_instance = Mock()
        mock_dataset_instance.title = "Existing Title"
        mock_dataset_instance.description = "Existing Description"
        mock_dataset.objects.get_or_create.return_value = (mock_dataset_instance, False)

        request = self.factory.get("/chooser/")
        request.user = self.user
        request.COOKIES = {}

        self.view.request = request
        result = self.view.get_object("dataset-123,2021,1,true")

        # Verify existing values were preserved (not overwritten by empty API values)
        self.assertEqual(mock_dataset_instance.title, "Existing Title")
        self.assertEqual(mock_dataset_instance.description, "Existing Description")

        # Verify save was NOT called since API values were empty/None
        mock_dataset_instance.save.assert_not_called()
        self.assertEqual(result, mock_dataset_instance)


class TestDatasetChosenMultipleViewMixin(TestCase):
    """Test the DatasetChosenMultipleViewMixin functionality."""

    def setUp(self):
        self.factory = RequestFactory()
        # Create a user for the request
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.view = DatasetChosenMultipleViewMixin()

    @patch("cms.datasets.views.user_can_access_unpublished_datasets")
    @patch("cms.datasets.views.Dataset")
    def test_get_objects_unpublished_without_permission_raises_error(self, mock_dataset, mock_permission_check):
        """Test that get_objects raises PermissionDenied for unpublished datasets without permission."""
        mock_permission_check.return_value = False

        request = self.factory.get("/chooser/")
        request.user = self.user
        request.COOKIES = {}

        self.view.request = request

        with self.assertRaises(PermissionDenied):
            self.view.get_objects(["dataset-123,2021,1,false"])

        # Verify permission check was called
        mock_permission_check.assert_called_once_with(self.user)
        # Verify no Datasets were created since permission was denied
        mock_dataset.objects.bulk_create.assert_not_called()

    @patch("cms.datasets.views.user_can_access_unpublished_datasets")
    @patch("cms.datasets.views.get_dataset_for_published_state")
    @patch("cms.datasets.views.Dataset")
    @patch("cms.datasets.views.ONSDataset")
    def test_get_objects_unpublished_with_permission_succeeds(
        self, mock_ons_dataset, mock_dataset, mock_get_dataset, mock_permission_check
    ):
        """Test that get_objects succeeds for unpublished datasets with permission."""
        mock_permission_check.return_value = True

        # Mock the API dataset
        mock_api_dataset = Mock()
        mock_api_dataset.title = "Test Dataset"
        mock_api_dataset.description = "Test Description"

        mock_queryset = MagicMock()
        mock_ons_dataset.objects = mock_queryset
        mock_queryset.get.return_value = mock_api_dataset

        mock_get_dataset.return_value = mock_api_dataset

        # Mock the Django Dataset queryset - first call returns empty list (existing_datasets_map)
        # second call (with `.using`) returns the final queryset after bulk_create
        mock_final_queryset = Mock()
        mock_dataset.objects.filter.return_value = []
        mock_dataset.objects.using.return_value.filter.return_value = mock_final_queryset
        mock_dataset.objects.bulk_create.return_value = None

        request = self.factory.get("/chooser/")
        request.user = self.user
        request.COOKIES = {}

        self.view.request = request
        result = self.view.get_objects(["dataset-123,2021,1,false"])

        # Verify the initial filter to find existing Datasets was called once
        mock_dataset.objects.filter.assert_called_once()
        # Verify permission check was called
        mock_permission_check.assert_called_once_with(self.user)
        # Verify Datasets were created
        mock_dataset.objects.bulk_create.assert_called_once()
        # Verify using(DEFAULT_DB_ALIAS) was called for final queryset
        mock_dataset.objects.using.assert_called_once_with(DEFAULT_DB_ALIAS)
        # Verify the results were fetched
        mock_dataset.objects.using.return_value.filter.assert_called_once()
        self.assertEqual(result, mock_final_queryset)

    @patch("cms.datasets.views.user_can_access_unpublished_datasets")
    @patch("cms.datasets.views.get_dataset_for_published_state")
    @patch("cms.datasets.views.ONSDataset")
    def test_get_objects_mixed_published_states_without_permission_raises_error(
        self, mock_ons_dataset, mock_get_dataset, mock_permission_check
    ):
        """Test that get_objects raises PermissionDenied if any dataset is unpublished and user lacks permission."""
        mock_permission_check.return_value = False

        # Mock the API dataset for the published one (processed first)
        mock_api_dataset_published = Mock()
        mock_api_dataset_published.title = "Published Dataset"
        mock_api_dataset_published.description = "Published Description"

        mock_queryset = MagicMock()
        mock_ons_dataset.objects = mock_queryset
        mock_queryset.get.return_value = mock_api_dataset_published

        mock_get_dataset.return_value = mock_api_dataset_published

        request = self.factory.get("/chooser/")
        request.user = self.user
        request.COOKIES = {}

        self.view.request = request

        # Mix of published and unpublished - should fail on the second (unpublished) one
        with self.assertRaises(PermissionDenied):
            self.view.get_objects(["dataset-123,2021,1,true", "dataset-456,2022,2,false"])

        # Verify permission check was called for the unpublished dataset
        mock_permission_check.assert_called_with(self.user)

    @patch("cms.datasets.views.get_dataset_for_published_state")
    @patch("cms.datasets.views.Dataset")
    @patch("cms.datasets.views.ONSDataset")
    def test_get_objects_published_without_permission_check(self, mock_ons_dataset, mock_dataset, mock_get_dataset):
        """Test that get_objects for published datasets does not require permission check."""
        # Mock the API dataset
        mock_api_dataset = Mock()
        mock_api_dataset.title = "Test Dataset"
        mock_api_dataset.description = "Test Description"

        mock_queryset = MagicMock()
        mock_ons_dataset.objects = mock_queryset
        mock_queryset.get.return_value = mock_api_dataset

        mock_get_dataset.return_value = mock_api_dataset

        # Mock the Django Dataset queryset - first call returns empty list (existing_datasets_map)
        # second call (with `.using`) returns the final queryset after bulk_create
        mock_final_queryset = Mock()
        mock_dataset.objects.filter.return_value = []
        mock_dataset.objects.using.return_value.filter.return_value = mock_final_queryset
        mock_dataset.objects.bulk_create.return_value = None

        request = self.factory.get("/chooser/")
        request.user = self.user
        request.COOKIES = {}

        self.view.request = request
        result = self.view.get_objects(["dataset-123,2021,1,true"])

        # Verify Datasets were created
        mock_dataset.objects.bulk_create.assert_called_once()
        self.assertEqual(result, mock_final_queryset)

    @patch("cms.datasets.views.get_dataset_for_published_state")
    @patch("cms.datasets.views.Dataset")
    @patch("cms.datasets.views.ONSDataset")
    def test_get_objects_with_token(self, mock_ons_dataset, mock_dataset, mock_get_dataset):
        """Test get_objects passes auth token when fetching datasets from API."""
        # Mock the API datasets
        mock_api_dataset_1 = Mock()
        mock_api_dataset_1.title = "Test Dataset 1"
        mock_api_dataset_1.description = "Test Description 1"

        mock_api_dataset_2 = Mock()
        mock_api_dataset_2.title = "Test Dataset 2"
        mock_api_dataset_2.description = "Test Description 2"

        mock_queryset = MagicMock()
        mock_ons_dataset.objects = mock_queryset
        mock_queryset.with_token.return_value = mock_queryset
        mock_queryset.get.side_effect = [mock_api_dataset_1, mock_api_dataset_2]

        mock_get_dataset.side_effect = [mock_api_dataset_1, mock_api_dataset_2]

        # Mock the Django Dataset queryset - first call returns empty list (existing_datasets_map)
        # second call returns the final queryset after bulk_create
        mock_final_queryset = Mock()
        mock_dataset.objects.filter.side_effect = [[], mock_final_queryset]
        mock_dataset.objects.bulk_create.return_value = None

        request = self.factory.get("/chooser/")
        request.user = self.user
        request.COOKIES = {settings.ACCESS_TOKEN_COOKIE_NAME: "test_token"}

        self.view.request = request
        self.view.get_objects(["dataset-123,2021,1,true", "dataset-456,2022,2,true"])

        # Verify token was passed (should be called twice, once for each dataset)
        self.assertEqual(mock_queryset.with_token.call_count, 2)
        mock_queryset.with_token.assert_called_with("test_token")

    @patch("cms.datasets.views.get_dataset_for_published_state")
    @patch("cms.datasets.views.Dataset")
    @patch("cms.datasets.views.ONSDataset")
    def test_get_objects_without_token(self, mock_ons_dataset, mock_dataset, mock_get_dataset):
        """Test get_objects works without auth token."""
        # Mock the API dataset
        mock_api_dataset = Mock()
        mock_api_dataset.title = "Test Dataset"
        mock_api_dataset.description = "Test Description"

        mock_queryset = MagicMock()
        mock_ons_dataset.objects = mock_queryset
        mock_queryset.get.return_value = mock_api_dataset

        mock_get_dataset.return_value = mock_api_dataset

        # Mock the Django Dataset queryset - first call returns empty list (existing_datasets_map)
        # second call returns the final queryset after bulk_create
        mock_final_queryset = Mock()
        mock_dataset.objects.filter.side_effect = [[], mock_final_queryset]
        mock_dataset.objects.bulk_create.return_value = None

        request = self.factory.get("/chooser/")
        request.user = self.user
        request.COOKIES = {}

        self.view.request = request
        self.view.get_objects(["dataset-123,2021,1,true"])

        # Verify with_token was NOT called
        mock_queryset.with_token.assert_not_called()
        mock_queryset.get.assert_called_once_with(pk="dataset-123")

    @patch("cms.datasets.views.get_dataset_for_published_state")
    @patch("cms.datasets.views.Dataset")
    @patch("cms.datasets.views.ONSDataset")
    def test_get_objects_updates_existing_datasets_with_changed_metadata(
        self, mock_ons_dataset, mock_dataset, mock_get_dataset
    ):
        """Test that existing datasets get bulk_update when API metadata changes."""
        # Mock the API dataset with updated metadata
        mock_api_dataset = Mock()
        mock_api_dataset.title = "Updated Title"
        mock_api_dataset.description = "Updated Description"

        mock_queryset = MagicMock()
        mock_ons_dataset.objects = mock_queryset
        mock_queryset.get.return_value = mock_api_dataset

        mock_get_dataset.return_value = mock_api_dataset

        # Mock existing dataset with old metadata
        existing_dataset = Mock()
        existing_dataset.namespace = "dataset-123"
        existing_dataset.edition = "2021"
        existing_dataset.version = 1
        existing_dataset.title = "Old Title"
        existing_dataset.description = "Old Description"

        mock_final_queryset = Mock()
        mock_using = Mock()
        mock_using.filter.return_value = mock_final_queryset
        mock_dataset.objects.filter.side_effect = [[existing_dataset]]
        mock_dataset.objects.using.return_value = mock_using
        mock_dataset.objects.bulk_create.return_value = None
        mock_dataset.objects.bulk_update.return_value = None

        request = self.factory.get("/chooser/")
        request.user = self.user
        request.COOKIES = {}

        self.view.request = request
        result = self.view.get_objects(["dataset-123,2021,1,true"])

        # Verify metadata was updated in memory
        self.assertEqual(existing_dataset.title, "Updated Title")
        self.assertEqual(existing_dataset.description, "Updated Description")

        # Verify bulk_update was called with the updated dataset
        mock_dataset.objects.bulk_create.assert_not_called()
        mock_dataset.objects.bulk_update.assert_called_once()
        call_args = mock_dataset.objects.bulk_update.call_args
        self.assertEqual(call_args[0][0], [existing_dataset])
        self.assertEqual(set(call_args[0][1]), {"title", "description"})
        self.assertEqual(result, mock_final_queryset)

    @patch("cms.datasets.views.get_dataset_for_published_state")
    @patch("cms.datasets.views.Dataset")
    @patch("cms.datasets.views.ONSDataset")
    def test_get_objects_skips_bulk_update_when_metadata_unchanged(
        self, mock_ons_dataset, mock_dataset, mock_get_dataset
    ):
        """Test that bulk_update is skipped when existing metadata matches API data."""
        # Mock the API dataset
        mock_api_dataset = Mock()
        mock_api_dataset.title = "Same Title"
        mock_api_dataset.description = "Same Description"

        mock_queryset = MagicMock()
        mock_ons_dataset.objects = mock_queryset
        mock_queryset.get.return_value = mock_api_dataset

        mock_get_dataset.return_value = mock_api_dataset

        # Mock existing dataset with matching metadata
        existing_dataset = Mock()
        existing_dataset.namespace = "dataset-123"
        existing_dataset.edition = "2021"
        existing_dataset.version = 1
        existing_dataset.title = "Same Title"
        existing_dataset.description = "Same Description"

        mock_dataset.objects.filter.side_effect = [[existing_dataset]]
        mock_dataset.objects.bulk_create.return_value = None

        request = self.factory.get("/chooser/")
        request.user = self.user
        request.COOKIES = {}

        self.view.request = request
        result = self.view.get_objects(["dataset-123,2021,1,true"])

        # Verify no bulk operations were performed since metadata matches
        mock_dataset.objects.bulk_update.assert_not_called()
        mock_dataset.objects.bulk_create.assert_not_called()

        # Since no operations were performed, there is no .using call.
        self.assertEqual(result, mock_dataset.objects.all.return_value)

    @patch("cms.datasets.views.get_dataset_for_published_state")
    @patch("cms.datasets.views.Dataset")
    @patch("cms.datasets.views.ONSDataset")
    def test_get_objects_handles_mixed_new_and_updated_datasets(self, mock_ons_dataset, mock_dataset, mock_get_dataset):
        """Test that get_objects handles both creating new and updating existing datasets."""
        # Mock two different API datasets
        mock_api_dataset_1 = Mock()
        mock_api_dataset_1.title = "New Dataset"
        mock_api_dataset_1.description = "New Description"

        mock_api_dataset_2 = Mock()
        mock_api_dataset_2.title = "Updated Dataset"
        mock_api_dataset_2.description = "Updated Description"

        mock_queryset = MagicMock()
        mock_ons_dataset.objects = mock_queryset
        mock_queryset.get.side_effect = [mock_api_dataset_1, mock_api_dataset_2]

        mock_get_dataset.side_effect = [mock_api_dataset_1, mock_api_dataset_2]

        # Only the second dataset exists
        existing_dataset = Mock()
        existing_dataset.namespace = "dataset-456"
        existing_dataset.edition = "2022"
        existing_dataset.version = 2
        existing_dataset.title = "Old Title"
        existing_dataset.description = "Old Description"

        mock_final_queryset = Mock()
        mock_using = Mock()
        mock_using.filter.return_value = mock_final_queryset
        mock_dataset.objects.filter.side_effect = [[existing_dataset]]
        mock_dataset.objects.using.return_value = mock_using
        mock_dataset.objects.bulk_create.return_value = None
        mock_dataset.objects.bulk_update.return_value = None

        request = self.factory.get("/chooser/")
        request.user = self.user
        request.COOKIES = {}

        self.view.request = request
        result = self.view.get_objects(["dataset-123,2021,1,true", "dataset-456,2022,2,true"])

        # Verify bulk_create was called for the new dataset
        self.assertEqual(mock_dataset.objects.bulk_create.call_count, 1)
        created_instances = mock_dataset.objects.bulk_create.call_args[0][0]
        self.assertEqual(len(created_instances), 1)

        # Verify bulk_update was called for the existing dataset
        self.assertEqual(mock_dataset.objects.bulk_update.call_count, 1)
        updated_instances = mock_dataset.objects.bulk_update.call_args[0][0]
        self.assertEqual(len(updated_instances), 1)
        self.assertEqual(updated_instances[0], existing_dataset)
        self.assertEqual(existing_dataset.title, "Updated Dataset")
        self.assertEqual(existing_dataset.description, "Updated Description")

        self.assertEqual(result, mock_final_queryset)

    @patch("cms.datasets.views.get_dataset_for_published_state")
    @patch("cms.datasets.views.Dataset")
    @patch("cms.datasets.views.ONSDataset")
    def test_get_objects_updates_only_changed_fields_in_bulk(self, mock_ons_dataset, mock_dataset, mock_get_dataset):
        """Test that bulk_update only includes datasets with changed fields."""
        # Mock two API datasets - one with changes, one without
        mock_api_dataset_1 = Mock()
        mock_api_dataset_1.title = "Updated Title"
        mock_api_dataset_1.description = "Updated Description"

        mock_api_dataset_2 = Mock()
        mock_api_dataset_2.title = "Same Title"
        mock_api_dataset_2.description = "Same Description"

        mock_queryset = MagicMock()
        mock_ons_dataset.objects = mock_queryset
        mock_queryset.get.side_effect = [mock_api_dataset_1, mock_api_dataset_2]

        mock_get_dataset.side_effect = [mock_api_dataset_1, mock_api_dataset_2]

        # Both datasets exist
        existing_dataset_1 = Mock()
        existing_dataset_1.namespace = "dataset-123"
        existing_dataset_1.edition = "2021"
        existing_dataset_1.version = 1
        existing_dataset_1.title = "Old Title"
        existing_dataset_1.description = "Old Description"

        existing_dataset_2 = Mock()
        existing_dataset_2.namespace = "dataset-456"
        existing_dataset_2.edition = "2022"
        existing_dataset_2.version = 2
        existing_dataset_2.title = "Same Title"
        existing_dataset_2.description = "Same Description"

        mock_final_queryset = Mock()
        mock_using = Mock()
        mock_using.filter.return_value = mock_final_queryset
        mock_dataset.objects.filter.side_effect = [[existing_dataset_1, existing_dataset_2]]
        mock_dataset.objects.using.return_value = mock_using
        mock_dataset.objects.bulk_create.return_value = None
        mock_dataset.objects.bulk_update.return_value = None

        request = self.factory.get("/chooser/")
        request.user = self.user
        request.COOKIES = {}

        self.view.request = request
        result = self.view.get_objects(["dataset-123,2021,1,true", "dataset-456,2022,2,true"])

        # Verify bulk_create was NOT called (both exist)
        mock_dataset.objects.bulk_create.assert_not_called()

        # Verify bulk_update was called with only the changed dataset
        self.assertEqual(mock_dataset.objects.bulk_update.call_count, 1)
        updated_instances = mock_dataset.objects.bulk_update.call_args[0][0]
        self.assertEqual(len(updated_instances), 1)
        self.assertEqual(updated_instances[0], existing_dataset_1)
        self.assertEqual(existing_dataset_1.title, "Updated Title")

        self.assertEqual(result, mock_final_queryset)

    @patch("cms.datasets.views.get_dataset_for_published_state")
    @patch("cms.datasets.views.Dataset")
    @patch("cms.datasets.views.ONSDataset")
    def test_get_objects_skips_update_when_api_has_empty_values(self, mock_ons_dataset, mock_dataset, mock_get_dataset):
        """Test that empty/None values from API don't trigger bulk updates."""
        # Mock API dataset with empty values
        mock_api_dataset = Mock()
        mock_api_dataset.title = None
        mock_api_dataset.description = ""

        mock_queryset = MagicMock()
        mock_ons_dataset.objects = mock_queryset
        mock_queryset.get.return_value = mock_api_dataset

        mock_get_dataset.return_value = mock_api_dataset

        # Mock existing dataset with valid values
        existing_dataset = Mock()
        existing_dataset.namespace = "dataset-123"
        existing_dataset.edition = "2021"
        existing_dataset.version = 1
        existing_dataset.title = "Existing Title"
        existing_dataset.description = "Existing Description"

        mock_dataset.objects.filter.side_effect = [[existing_dataset]]
        mock_dataset.objects.bulk_create.return_value = None

        request = self.factory.get("/chooser/")
        request.user = self.user
        request.COOKIES = {}

        self.view.request = request
        result = self.view.get_objects(["dataset-123,2021,1,true"])

        # Verify existing values were preserved (not overwritten by empty API values)
        self.assertEqual(existing_dataset.title, "Existing Title")
        self.assertEqual(existing_dataset.description, "Existing Description")

        # Verify no bulk operations were performed since API values were empty
        mock_dataset.objects.bulk_update.assert_not_called()
        mock_dataset.objects.bulk_create.assert_not_called()

        # Since no operations were performed, there is no .using call.
        self.assertEqual(result, mock_dataset.objects.all.return_value)
