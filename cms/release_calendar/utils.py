from datetime import date

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
