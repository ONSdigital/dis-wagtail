import logging

import pytest


@pytest.mark.django_db
def test_csrf_token_mismatch_logs_an_error(csrf_check_client, caplog, enable_console_logging):  # pylint: disable=unused-argument
    csrf_check_client.cookies["csrftoken"] = "wrong"

    with caplog.at_level(logging.ERROR, logger="django.security.csrf"):
        csrf_check_client.post("/admin/login/", {})

    assert "CSRF Failure: CSRF cookie" in caplog.text
