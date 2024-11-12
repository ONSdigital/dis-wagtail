from behave_django.environment import BehaveHooksMixin
from behave_django.testcase import BehaviorDrivenTestMixin
from django.test import LiveServerTestCase
from django.test.runner import DiscoverRunner


class BehaviorDrivenLiveTestCase(BehaviorDrivenTestMixin, LiveServerTestCase):
    """A behaviour driven test case using the LiveServerTestCase instead of the default StaticLiveServerTestCase."""


class BehaveDjangoLiveServerTestRunner(DiscoverRunner, BehaveHooksMixin):
    """A behave Django test runner utilising the LiveServerTestCase instead of the default StaticLiveServerTestCase."""

    testcase_class = BehaviorDrivenLiveTestCase
