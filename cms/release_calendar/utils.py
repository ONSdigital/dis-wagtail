from datetime import date, datetime
from typing import TYPE_CHECKING

from django.utils.translation import gettext, override

if TYPE_CHECKING:
    from .models import ReleaseCalendarPage
FULL_ENGLISH_MONTHS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]

FULL_WELSH_MONTHS = [
    "Ionawr",
    "Chwefror",
    "Mawrth",
    "Ebrill",
    "Mai",
    "Mehefin",
    "Gorffennaf",
    "Awst",
    "Medi",
    "Hydref",
    "Tachwedd",
    "Rhagfyr",
]

DATE_MONTHS = {
    "en": FULL_ENGLISH_MONTHS,
    "cy": FULL_WELSH_MONTHS,
}


def parse_month_year(text: str, locale_code: str) -> date | None:
    """Parses a month and year string into a date object."""
    parts = text.split(" ", maxsplit=1)
    # PLR2004: https://docs.astral.sh/ruff/rules/magic-value-comparison/
    if len(parts) != 2:  # noqa: PLR2004
        return None

    [month, year] = parts

    if month not in DATE_MONTHS.get(locale_code, []) or len(year) != 4:  # noqa: PLR2004
        return None

    try:
        return date(int(year), DATE_MONTHS[locale_code].index(month) + 1, 1)
    except ValueError:
        return None


def parse_day_month_year_time(text: str, locale_code: str) -> datetime | None:
    """Parses a day, month, year, and time string into a datetime object."""
    parts = text.split(" ", maxsplit=3)
    # PLR2004: https://docs.astral.sh/ruff/rules/magic-value-comparison/
    if len(parts) != 4:  # noqa: PLR2004
        return None

    [day, month, year, time] = parts

    if month not in DATE_MONTHS.get(locale_code, []) or len(year) != 4 or not day.isdigit():  # noqa: PLR2004
        return None

    try:
        month_index = DATE_MONTHS[locale_code].index(month) + 1
        return datetime.strptime(f"{year}-{month_index}-{day} {time}+0000", "%Y-%m-%d %I:%M%p%z")
    except ValueError:
        return None


def get_translated_string(string_to_translate: str, language_code: str) -> str:
    """Translates a string to a specific language.

    Note that in most cases you would use the `gettext` or `gettext_lazy` functions directly in your templates or views.
    This function is provided for cases where you need to translate a string programmatically.

    Args:
      string_to_translate: The string to be translated.
      language_code: The language code for the desired translation (e.g., 'cy' for Welsh).

    Returns:
      The translated string.
    """
    with override(language_code):
        translated_string = gettext(string_to_translate)
    return translated_string


def get_release_calendar_page_details(
    release_calendar_page: "ReleaseCalendarPage",
) -> str:
    """Returns the release page title, status and release date."""
    return (
        f"{release_calendar_page.title} "
        f"({release_calendar_page.specific_deferred.get_status_display()}, "
        f"{release_calendar_page.specific_deferred.release_date_value})"
    )
