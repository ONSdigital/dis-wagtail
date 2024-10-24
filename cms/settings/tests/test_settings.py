import pytest


@pytest.mark.django_db
def test_referrer_policy(client):
    """Test that we have a Referrer-Policy header."""
    response = client.get("/")
    assert response["Referrer-Policy"] == "no-referrer-when-downgrade"
