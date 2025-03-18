from typing import ClassVar

from django.test import TestCase
from wagtail.admin.forms.choosers import BaseFilterForm

from cms.datasets.views import DatasetSearchFilterMixin


class ExampleSearchableModel:
    title = "foo example"
    description = "bar"
    not_searched = "no match"

    search_fields: ClassVar = ["title", "description"]


class ExampleFilterForm(DatasetSearchFilterMixin, BaseFilterForm): ...


class TestDatasetSearchFilterMixin(TestCase):
    def test_filter(self):
        obj1 = ExampleSearchableModel()
        obj2 = ExampleSearchableModel()
        obj2.title = "eggs"
        obj2.description = "spam example"

        objects = [obj1, obj2]

        filter_form = ExampleFilterForm()
        filter_form.cleaned_data = {}  # pylint: disable=attribute-defined-outside-init
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
