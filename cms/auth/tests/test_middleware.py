import uuid
from unittest import mock

from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase, override_settings

from cms.auth.middleware import JWT_SESSION_ID_KEY, ONSAuthMiddleware
from cms.users.models import User


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
        user = User.objects.create(username="test", email="test@example.com")
        user.external_user_id = str(uuid.uuid4())
        user.set_unusable_password()
        user.save()

        with (
            # AuthenticationMiddleware will resolve to this user
            mock.patch("django.contrib.auth.get_user", return_value=user),
            # we only want to spy on the helper, not replace it
            mock.patch.object(
                self.middleware,
                "_handle_cognito_disabled",
                wraps=self.middleware._handle_cognito_disabled,  # pylint: disable=protected-access  # keep original behaviour
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
        WAGTAIL_CORE_ADMIN_LOGIN_ENABLED=False,
    )
    def test_cognito_enabled_no_tokens_logs_out(self):
        req = self._request()
        req.COOKIES = {}  # no cookies at all

        user = User.objects.create(username="test", email="test@example.com")

        with (
            mock.patch("django.contrib.auth.get_user", return_value=user),
            mock.patch.object(
                self.middleware,
                "_handle_unauthenticated_user",
                wraps=self.middleware._handle_unauthenticated_user,  # pylint: disable=protected-access
            ) as m_unauth,
            mock.patch("cms.auth.middleware.logout") as m_logout,
        ):
            self.middleware.process_request(req)

            # correct branch taken
            m_unauth.assert_called_once_with(req)
            # logout executed
            m_logout.assert_called_once_with(req)

    # Cognito disabled and user has a local password -> should not logout
    @override_settings(AWS_COGNITO_LOGIN_ENABLED=False)
    def test_cognito_disabled_user_with_password_not_logged_out(self):
        req = self._request()
        user = User.objects.create_superuser(username="test", email="test@example.com")
        self.client.force_login(user)

        with (
            mock.patch("django.contrib.auth.get_user", return_value=user),
            mock.patch("cms.auth.middleware.logout") as m_logout,
        ):
            self.middleware.process_request(req)
            # Assert user is authenticated before checking logout
            self.assertTrue(user.is_authenticated)
            m_logout.assert_not_called()

    # Wagtail admin login on and usable password -> stay logged-in
    @override_settings(
        AWS_COGNITO_LOGIN_ENABLED=True,
        WAGTAIL_CORE_ADMIN_LOGIN_ENABLED=True,  # allows username/ password login
        ACCESS_TOKEN_COOKIE_NAME="a",
        ID_TOKEN_COOKIE_NAME="i",
    )
    def test_missing_tokens_but_wagtail_login_enabled_and_password_not_logged_out(self):
        req = self._request()
        req.COOKIES = {}  # no JWT cookies
        req = self._request()
        user = User.objects.create_superuser(username="test", email="test@example.com")
        self.client.force_login(user)

        with (
            mock.patch("django.contrib.auth.get_user", return_value=user),
            mock.patch("cms.auth.middleware.logout") as m_logout,
        ):
            self.middleware.process_request(req)
            self.assertTrue(user.is_authenticated)
            m_logout.assert_not_called()

    # Positive path for _validate_client_ids -> _authenticate_user reached
    @override_settings(
        AWS_COGNITO_LOGIN_ENABLED=True,
        AWS_COGNITO_APP_CLIENT_ID="expected",
        ACCESS_TOKEN_COOKIE_NAME="access",
        ID_TOKEN_COOKIE_NAME="id",
    )
    def test_valid_client_ids_authentication_successful(self):
        req = self._request()
        req.COOKIES = {"access": "tokA", "id": "tokI"}

        payload_access = {
            "client_id": "expected",
            "username": "user1",
            "jti": "ja",
            "token_use": "access",
        }
        payload_id = {
            "aud": "expected",
            "cognito:username": "user1",
            "jti": "jb",
            "email": "u@example.com",
            "token_use": "id",
        }

        with (
            mock.patch("cms.auth.middleware.validate_jwt", side_effect=[payload_access, payload_id]),
            mock.patch.object(ONSAuthMiddleware, "_authenticate_user") as m_auth,
        ):
            self.middleware.process_request(req)
            m_auth.assert_called_once()  # reached -> positive client-ID path

    # Negative path for _validate_client_ids -> _authenticate_user NOT reached
    @override_settings(
        AWS_COGNITO_LOGIN_ENABLED=True,
        AWS_COGNITO_APP_CLIENT_ID="expected-client-id",
        ACCESS_TOKEN_COOKIE_NAME="access",
        ID_TOKEN_COOKIE_NAME="id",
    )
    def test_invalid_client_ids_authentication_not_called(self):
        req = self._request()
        req.COOKIES = {"access": "tokA", "id": "tokI"}

        # client_id and aud do not match expected
        payload_access = {
            "client_id": "wrong-client-id",
            "username": "user1",
            "jti": "ja",
            "token_use": "access",
        }
        payload_id = {
            "aud": "wrong-client-id",
            "cognito:username": "user1",
            "jti": "jb",
            "email": "u@example.com",
            "token_use": "id",
        }

        with (
            mock.patch("cms.auth.middleware.validate_jwt", side_effect=[payload_access, payload_id]),
            mock.patch.object(ONSAuthMiddleware, "_authenticate_user") as m_auth,
            mock.patch("cms.auth.middleware.logout") as m_logout,
        ):
            self.middleware.process_request(req)
            m_auth.assert_not_called()  # _authenticate_user should NOT be called
            m_logout.assert_called_once()  # logout should be called due to client_id mismatch

    # Invalid tokens -> validate_jwt returns None
    @override_settings(
        AWS_COGNITO_LOGIN_ENABLED=True,
        ACCESS_TOKEN_COOKIE_NAME="access",
        ID_TOKEN_COOKIE_NAME="id",
    )
    def test_invalid_tokens_logout(self):
        req = self._request()
        req.COOKIES = {"access": "a", "id": "b"}
        with (
            mock.patch("cms.auth.middleware.validate_jwt", return_value=None),
            mock.patch("cms.auth.middleware.logout") as m_logout,
        ):
            self.middleware.process_request(req)
            m_logout.assert_called_once()

    # Authenticated but session missing jwt_session_id  -> authenticate and save
    @override_settings(
        AWS_COGNITO_LOGIN_ENABLED=True,
        AWS_COGNITO_APP_CLIENT_ID="expected",
        ACCESS_TOKEN_COOKIE_NAME="access",
        ID_TOKEN_COOKIE_NAME="id",
    )
    def test_session_without_jwt_key_triggers_authenticate_and_saves_key(self):
        req = self._request()
        req.COOKIES = {"access": "tokA", "id": "tokI"}

        payload_access = {"client_id": "expected", "username": "u1", "jti": "ja", "token_use": "access"}
        payload_id = {"aud": "expected", "cognito:username": "u1", "jti": "jb", "email": "e", "token_use": "id"}

        with (
            mock.patch("cms.auth.middleware.validate_jwt", side_effect=[payload_access, payload_id]),
            mock.patch.object(ONSAuthMiddleware, "_authenticate_user") as m_auth,
        ):
            self.middleware.process_request(req)
            m_auth.assert_called_once()
            self.assertEqual(req.session[JWT_SESSION_ID_KEY], "jajb")

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
        payload_access = {"client_id": "wrong", "username": "u1", "jti": "ja", "token_use": "access"}
        payload_id = {
            "aud": "wrong",
            "cognito:username": "u1",
            "jti": "jb",
            "email": "e@example.com",
            "token_use": "id",
        }

        with (
            mock.patch("cms.auth.middleware.validate_jwt", side_effect=[payload_access, payload_id]),
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
        req.session[JWT_SESSION_ID_KEY] = "jajb"
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
        user = User.objects.create(username="u1", email="u1@example.com")

        with (
            mock.patch("django.contrib.auth.get_user", return_value=user),
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
        req.session = {}
        req.COOKIES = {"access": "tokA", "id": "tokID"}
        payload_access = {"client_id": "expected", "username": "u1", "jti": "ja", "token_use": "access"}
        payload_id = {
            "aud": "expected",
            "cognito:username": "u1",
            "jti": "jb",
            "email": "e",
            "token_use": "id",
            "cognito:groups": ["g1"],
        }

        with (
            mock.patch("cms.auth.middleware.validate_jwt", side_effect=[payload_access, payload_id]),
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

        self.assertTrue(User.objects.filter(external_user_id=uid).exists())
        self.assertEqual(req.session[JWT_SESSION_ID_KEY], "jajb")

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
            mock.patch("cms.auth.middleware.validate_jwt", side_effect=[payload_access, payload_id]),
            mock.patch("cms.auth.middleware.logout") as m_logout,
        ):
            self.middleware.process_request(req)
            self.assertFalse(req.user.is_authenticated)
            m_logout.assert_called_once()

    # Existing user created=False -> update_details called
    @override_settings(
        AWS_COGNITO_LOGIN_ENABLED=True,
        AWS_COGNITO_APP_CLIENT_ID="expected",
        ACCESS_TOKEN_COOKIE_NAME="access",
        ID_TOKEN_COOKIE_NAME="id",
    )
    def test_existing_user_update_details_called(self):
        req = self._request()
        req.COOKIES = {"access": "tokA", "id": "tokI"}

        payload_access = {"client_id": "expected", "username": "user99", "jti": "ja", "token_use": "access"}
        payload_id = {
            "aud": "expected",
            "cognito:username": "user99",
            "jti": "jb",
            "email": "user99@example.com",
            "given_name": "U",
            "family_name": "Ser",
            "token_use": "id",
        }

        existing_user = User.objects.create(
            username="user99",
            email="user99@example.com",
            first_name="U",
            last_name="Ser",
        )
        existing_user.update_details = mock.Mock()

        with (
            mock.patch("cms.auth.middleware.validate_jwt", side_effect=[payload_access, payload_id]),
            mock.patch("cms.auth.middleware.User.objects.get_or_create", return_value=(existing_user, False)),
            mock.patch("cms.auth.middleware.login"),  # login() not called
        ):
            self.middleware.process_request(req)

        existing_user.update_details.assert_called_once_with(
            email="user99@example.com",
            first_name="U",
            last_name="Ser",
            created=False,
        )

    @override_settings(
        AWS_COGNITO_LOGIN_ENABLED=True,
        AWS_COGNITO_APP_CLIENT_ID="expected",
        ACCESS_TOKEN_COOKIE_NAME="access",
        ID_TOKEN_COOKIE_NAME="id",
    )
    def test_existing_user_details_are_updated(self):
        req = self._request()
        req.COOKIES = {"access": "tokA", "id": "tokI"}

        payload_access = {
            "client_id": "expected",
            "username": "user99",
            "jti": "ja",
            "token_use": "access",
        }
        payload_id = {
            "aud": "expected",
            "cognito:username": "user99",
            "jti": "jb",
            "email": "new_email@example.com",
            "given_name": "NewFirst",
            "family_name": "NewLast",
            "token_use": "id",
        }

        # Create an existing user with old details
        existing_user = User.objects.create(
            username="user99",
            email="old_email@example.com",
            first_name="OldFirst",
            last_name="OldLast",
        )
        # Mock update_details to track calls
        existing_user.update_details = mock.Mock()

        with (
            mock.patch("cms.auth.middleware.validate_jwt", side_effect=[payload_access, payload_id]),
            mock.patch("cms.auth.middleware.User.objects.get_or_create", return_value=(existing_user, False)),
            mock.patch("cms.auth.middleware.login"),  # Prevent actual login
        ):
            self.middleware.process_request(req)

        existing_user.update_details.assert_called_once_with(
            email="new_email@example.com",
            first_name="NewFirst",
            last_name="NewLast",
            created=False,
        )

    # _authenticate_user assigns groups and calls login()
    @override_settings(
        AWS_COGNITO_LOGIN_ENABLED=True,
        AWS_COGNITO_APP_CLIENT_ID="expected",
        ACCESS_TOKEN_COOKIE_NAME="access",
        ID_TOKEN_COOKIE_NAME="id",
    )
    def test_authenticate_user_assigns_groups_and_calls_login(self):
        req = self._request()
        req.COOKIES = {"access": "tokA", "id": "tokI"}

        payload_access = {"client_id": "expected", "username": "g-tester", "jti": "ja", "token_use": "access"}
        payload_id = {
            "aud": "expected",
            "cognito:username": "g-tester",
            "jti": "jb",
            "email": "g@test.com",
            "token_use": "id",
            "cognito:groups": ["role-admin", "team-alpha"],
        }

        user = User.objects.create(
            username="g-tester",
            email="g@test.com",
        )
        user.assign_groups_and_teams = mock.Mock()

        with (
            mock.patch("cms.auth.middleware.validate_jwt", side_effect=[payload_access, payload_id]),
            mock.patch("cms.auth.middleware.User.objects.get_or_create", return_value=(user, True)),
            mock.patch("cms.auth.middleware.login") as m_login,
        ):
            self.middleware.process_request(req)

        user.assign_groups_and_teams.assert_called_once_with(["role-admin", "team-alpha"])
        m_login.assert_called_once_with(req, user)

    @override_settings(AWS_COGNITO_LOGIN_ENABLED=True)
    def test_internal_health_endpoints_bypass_auth(self):
        for path in ("/-/readiness", "/-/liveness", "/-/health", "/health"):
            with self.subTest(path=path):
                req = self._request(path=path)
                req.COOKIES = {}  # no cookies, simulating unauthenticated internal API requests

                with (
                    mock.patch.object(
                        self.middleware,
                        "_handle_unauthenticated_user",
                        wraps=self.middleware._handle_unauthenticated_user,  # pylint: disable=protected-access
                    ) as m_unauth,
                    mock.patch("cms.auth.middleware.logout") as m_logout,
                ):
                    self.middleware.process_request(req)

                    # Check that the unauthenticated handler was NOT called, must be bypassed
                    m_unauth.assert_not_called()
                    # No logout should occur when auth is bypassed
                    m_logout.assert_not_called()
