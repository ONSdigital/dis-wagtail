import json

from django.test import TestCase
from jinja2 import ChainableUndefined

from cms.core.jinja2 import custom_json_dumps


class TestCustomJsonDumps(TestCase):
    def test_empty_dict(self):
        self.assertEqual(custom_json_dumps({}), "{}")

    def test_dict_with_chainable_undefined(self):
        chainable_undefined: ChainableUndefined = ChainableUndefined()
        self.assertEqual('{"key": null}', custom_json_dumps({"key": chainable_undefined}))

    def test_normal_encoder_fails_with_chainable_undefined(self):
        self.assertRaises(TypeError, json.dumps, {"key": ChainableUndefined()})

    def test_dict_with_none_value(self):
        self.assertEqual('{"key": null}', custom_json_dumps({"key": None}))

    def test_dict_with_nonserializable_value(self):
        self.assertRaises(TypeError, custom_json_dumps, {"key": object()})
