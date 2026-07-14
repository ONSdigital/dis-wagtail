from collections.abc import Generator
from contextlib import contextmanager

import factory
import factory.random


def get_default_locale() -> str:
    return str(factory.Faker._DEFAULT_LOCALE)  # pylint: disable=protected-access


def _set_default_locale(locale: str) -> None:
    factory.Faker._DEFAULT_LOCALE = locale  # pylint: disable=protected-access


@contextmanager
def seeded_randomness(seed: int, locale: str) -> Generator[None]:
    original_locale = get_default_locale()
    original_state = factory.random.get_random_state()  # type: ignore[no-untyped-call]

    _set_default_locale(locale)
    factory.random.reseed_random(seed)  # type: ignore[no-untyped-call]

    try:
        yield
    finally:
        _set_default_locale(original_locale)
        factory.random.set_random_state(original_state)  # type: ignore[no-untyped-call]
