from datetime import datetime

import pytest
from django.template import Context, Template


@pytest.mark.django_db
def test_referrer_policy(client):
    """Test that we have a Referrer-Policy header."""
    response = client.get("/")
    assert response["Referrer-Policy"] == "no-referrer-when-downgrade"


def test_date_format():
    """Test that DATETIME_FORMAT is our preferred one."""
    template = Template("{{ date|date:'DATETIME_FORMAT' }}")
    date = datetime(2024, 11, 1, 13, 0)
    rendered = template.render(Context({"date": date}))
    assert rendered == "1 November 2024 1:00p.m."
