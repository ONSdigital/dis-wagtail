import uuid
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase, override_settings

from cms.auth.middleware import JWT_SESSION_ID_KEY, ONSAuthMiddleware


class ONSAuthMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.get_response = lambda r: r  # middleware no-op response
        self.middleware = ONSAuthMiddleware(self.get_response)

    def _request(self, path="/admin/"):
        """Build a RequestFactory request and attach a fully-featured
        SessionStore by running SessionMiddleware.
        """
        req = self.factory.get(path)

        session_mw = SessionMiddleware(lambda r: None)
        session_mw.process_request(req)  # adds request.session
        req.session.save()  # initialises session_key/cookies

        return req

    # Feature flag -> Cognito disabled
    @override_settings(AWS_COGNITO_LOGIN_ENABLED=False)
    def test_cognito_disabled_logs_out_user_without_password(self):
        req = self._request()
        fake_user = mock.Mock(
            is_authenticated=True,
            has_usable_password=lambda: False,
            user_id="x",
        )

        with (
            # AuthenticationMiddleware will resolve to this user
            mock.patch("django.contrib.auth.get_user", return_value=fake_user),
            # we only want to spy on the helper, not replace it
            mock.patch.object(
                self.middleware,
                "_handle_cognito_disabled",
                wraps=self.middleware._handle_cognito_disabled,  # keep original behaviour
            ) as m_disabled,
            mock.patch("cms.auth.middleware.logout") as m_logout,
        ):
            self.middleware.process_request(req)

            # correct branch taken
            m_disabled.assert_called_once_with(req)
            # and it resulted in a logout
            m_logout.assert_called_once_with(req)

    # Missing cookies -> logout
    @override_settings(
        AWS_COGNITO_LOGIN_ENABLED=True,
        ACCESS_TOKEN_COOKIE_NAME="access",
        ID_TOKEN_COOKIE_NAME="id",
        WAGTAIL_CORE_ADMIN_LOGIN_ENABLED=False,
    )
    def test_no_tokens_logs_out(self):
        req = self._request()
        req.COOKIES = {}  # no cookies at all

        fake_user = mock.Mock(
            is_authenticated=True,
            has_usable_password=lambda: False,
            user_id="u1",
        )

        with (
            mock.patch("django.contrib.auth.get_user", return_value=fake_user),
            mock.patch.object(
                self.middleware,
                "_handle_unauthenticated_user",
                wraps=self.middleware._handle_unauthenticated_user,
            ) as m_unauth,
            mock.patch("cms.auth.middleware.logout") as m_logout,
        ):
            self.middleware.process_request(req)

            # correct branch taken
            m_unauth.assert_called_once_with(req)
            # logout executed
            m_logout.assert_called_once_with(req)

    # Invalid tokens -> validate_jwt returns None
    @override_settings(
        AWS_COGNITO_LOGIN_ENABLED=True,
        ACCESS_TOKEN_COOKIE_NAME="access",
        ID_TOKEN_COOKIE_NAME="id",
    )
    def test_invalid_tokens_logout(self):
        req = self._request()
        req.COOKIES = {"access": "a", "id": "b"}
        req.user = mock.Mock(is_authenticated=False)
        with (
            mock.patch("cms.auth.middleware.validate_jwt", return_value=None),
            mock.patch("cms.auth.middleware.logout") as m_logout,
        ):
            self.middleware.process_request(req)
            m_logout.assert_called_once()

    #  Client-ID mismatch
    @override_settings(
        AWS_COGNITO_LOGIN_ENABLED=True,
        AWS_COGNITO_APP_CLIENT_ID="expected",
        ACCESS_TOKEN_COOKIE_NAME="access",
        ID_TOKEN_COOKIE_NAME="id",
    )
    def test_client_id_mismatch(self):
        req = self._request()
        req.COOKIES = {"access": "tokA", "id": "tokID"}
        req.user = mock.Mock(is_authenticated=False)
        mock_payload_access = {"client_id": "wrong", "username": "u1", "jti": "ja", "token_use": "access"}
        mock_payload_id = {
            "aud": "wrong",
            "cognito:username": "u1",
            "jti": "jb",
            "email": "e@example.com",
            "token_use": "id",
        }

        with (
            mock.patch("cms.auth.middleware.validate_jwt", side_effect=[mock_payload_access, mock_payload_id]),
            mock.patch("cms.auth.middleware.logout") as m_logout,
        ):
            self.middleware.process_request(req)
            m_logout.assert_called_once()

    # Session replay / skip re-auth
    @override_settings(
        AWS_COGNITO_LOGIN_ENABLED=True,
        AWS_COGNITO_APP_CLIENT_ID="expected",
        ACCESS_TOKEN_COOKIE_NAME="access",
        ID_TOKEN_COOKIE_NAME="id",
    )
    def test_session_key_skips_authenticate(self):
        req = self._request()
        req.session = {JWT_SESSION_ID_KEY: "jajb"}  # up-to-date
        req.COOKIES = {"access": "tokA", "id": "tokID"}

        payload_access = {
            "client_id": "expected",
            "username": "u1",
            "jti": "ja",
            "token_use": "access",
        }
        payload_id = {
            "aud": "expected",
            "cognito:username": "u1",
            "jti": "jb",
            "email": "e",
            "token_use": "id",
        }

        # authenticated user that matches the token username
        fake_user = mock.Mock(is_authenticated=True, user_id="u1")

        with (
            mock.patch("django.contrib.auth.get_user", return_value=fake_user),
            mock.patch("cms.auth.middleware.validate_jwt", side_effect=[payload_access, payload_id]),
            mock.patch.object(ONSAuthMiddleware, "_authenticate_user") as m_auth,
        ):
            self.middleware.process_request(req)
            m_auth.assert_not_called()

    # Fresh authenticate path
    @override_settings(
        AWS_COGNITO_LOGIN_ENABLED=True,
        AWS_COGNITO_APP_CLIENT_ID="expected",
        ACCESS_TOKEN_COOKIE_NAME="access",
        ID_TOKEN_COOKIE_NAME="id",
    )
    def test_authenticate_user_called_and_session_key_written(self):
        req = self._request()
        req.user = mock.Mock(is_authenticated=False)
        req.session = {}
        req.COOKIES = {"access": "tokA", "id": "tokID"}
        payload = {"client_id": "expected", "username": "u1", "jti": "ja", "token_use": "access"}
        payload_id = {
            "aud": "expected",
            "cognito:username": "u1",
            "jti": "jb",
            "email": "e",
            "token_use": "id",
            "cognito:groups": ["g1"],
        }

        with (
            mock.patch("cms.auth.middleware.validate_jwt", side_effect=[payload, payload_id]),
            mock.patch.object(ONSAuthMiddleware, "_authenticate_user") as m_auth,
        ):
            self.middleware.process_request(req)
            m_auth.assert_called_once()
            self.assertEqual(req.session[JWT_SESSION_ID_KEY], "jajb")

    # First login -> user created, session key persisted
    @override_settings(
        AWS_COGNITO_LOGIN_ENABLED=True,
        AWS_COGNITO_APP_CLIENT_ID="expected",
        ACCESS_TOKEN_COOKIE_NAME="access",
        ID_TOKEN_COOKIE_NAME="id",
    )
    def test_first_login_creates_user_and_saves_session(self):
        req = self._request()
        req.user = mock.Mock(is_authenticated=False)

        req.COOKIES = {"access": "tokA", "id": "tokID"}

        uid = str(uuid.uuid4())

        payload_access = {
            "client_id": "expected",
            "username": uid,
            "jti": "ja",
            "token_use": "access",
        }
        payload_id = {
            "aud": "expected",
            "cognito:username": uid,
            "jti": "jb",
            "email": "e@example.com",
            "token_use": "id",
            "cognito:groups": ["role-admin"],
        }

        with mock.patch(
            "cms.auth.middleware.validate_jwt",
            side_effect=[payload_access, payload_id],
        ):
            self.middleware.process_request(req)

        User = get_user_model()
        assert User.objects.filter(user_id=uid).exists()
        assert req.session[JWT_SESSION_ID_KEY] == "jajb"

    # Token rotation (new jti) -> re-authenticate and update session key
    @override_settings(
        AWS_COGNITO_LOGIN_ENABLED=True,
        AWS_COGNITO_APP_CLIENT_ID="expected",
        ACCESS_TOKEN_COOKIE_NAME="access",
        ID_TOKEN_COOKIE_NAME="id",
    )
    def test_token_rotation_triggers_reauth(self):
        req = self._request()
        req.session = {}
        req.user = mock.Mock(is_authenticated=True, user_id="u1")

        req.COOKIES = {"access": "tokA", "id": "tokID"}

        # first request jtIs
        p1a = {"client_id": "expected", "username": "u1", "jti": "a1", "token_use": "access"}
        p1i = {"aud": "expected", "cognito:username": "u1", "jti": "b1", "email": "e", "token_use": "id"}

        # rotated jtIs on second request
        p2a = {**p1a, "jti": "a2"}
        p2i = {**p1i, "jti": "b2"}

        with (
            mock.patch(
                "cms.auth.middleware.validate_jwt",
                side_effect=[p1a, p1i, p2a, p2i],
            ),
            mock.patch.object(ONSAuthMiddleware, "_authenticate_user") as m_auth,
        ):
            self.middleware.process_request(req)  # first request
            self.assertEqual(req.session[JWT_SESSION_ID_KEY], "a1b1")

            self.middleware.process_request(req)  # second request (rotated)
            self.assertEqual(req.session[JWT_SESSION_ID_KEY], "a2b2")

        # called once per request because jtIs changed
        self.assertEqual(m_auth.call_count, 2)

    # Username mismatch across tokens -> logout
    @override_settings(
        AWS_COGNITO_LOGIN_ENABLED=True,
        AWS_COGNITO_APP_CLIENT_ID="expected",
        ACCESS_TOKEN_COOKIE_NAME="access",
        ID_TOKEN_COOKIE_NAME="id",
    )
    def test_username_mismatch_across_tokens_logout(self):
        req = self._request()
        req.COOKIES = {"access": "tokA", "id": "tokID"}
        req.user = mock.Mock(is_authenticated=False)

        payload_access = {
            "client_id": "expected",
            "username": "userA",
            "jti": "ja",
            "token_use": "access",
        }
        payload_id = {
            "aud": "expected",
            "cognito:username": "userB",
            "jti": "jb",
            "email": "x@y.com",
            "token_use": "id",
        }

        with (
            mock.patch("cms.auth.middleware.validate_jwt", side_effect=[payload_access, payload_id]),
            mock.patch("cms.auth.middleware.logout") as m_logout,
        ):
            self.middleware.process_request(req)
            m_logout.assert_called_once()

    # Session user != token user -> logout
    @override_settings(
        AWS_COGNITO_LOGIN_ENABLED=True,
        AWS_COGNITO_APP_CLIENT_ID="expected",
        ACCESS_TOKEN_COOKIE_NAME="access",
        ID_TOKEN_COOKIE_NAME="id",
    )
    def test_session_user_differs_from_token_user_logout(self):
        req = self._request()
        req.COOKIES = {"access": "tokA", "id": "tokID"}

        uuid_a = str(uuid.uuid4())  # session user
        uuid_b = str(uuid.uuid4())  # token user (different)

        fake_user = mock.Mock(is_authenticated=True, user_id=uuid_a)

        payload_access = {
            "client_id": "expected",
            "username": uuid_a,
            "jti": "ja",
            "token_use": "access",
        }
        payload_id = {
            "aud": "expected",
            "cognito:username": uuid_b,
            "jti": "jb",
            "email": "x@y.com",
            "token_use": "id",
        }

        with (
            mock.patch("django.contrib.auth.get_user", return_value=fake_user),
            mock.patch("cms.auth.middleware.validate_jwt", side_effect=[payload_access, payload_id]),
            mock.patch("cms.auth.middleware.logout") as m_logout,
        ):
            self.middleware.process_request(req)
            m_logout.assert_called_once()
