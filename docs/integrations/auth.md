# Authentication

The Wagtail CMS integrates with the existing Authentication service which is powered by AWS Cognito
and interfaced via Florence (the old CMS) while both systems are in use.

This is the first phase towards ONS-wide Single Sign-On.

## Environment variables

| Var                                | Notes                                                                                                                                                                                              |
| ---------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `WAGTAIL_CORE_ADMIN_LOGIN_ENABLED` | Set to "true" to allow logins with Wagtail accounts                                                                                                                                                |
| `AWS_COGNITO_LOGIN_ENABLED`        | Set to "true" to enable the integration                                                                                                                                                            |
| `AUTH_TOKEN_REFRESH_URL`           | The Auth service endpoint for refreshing tokens                                                                                                                                                    |
| `AWS_COGNITO_USER_POOL_ID`         | The Cognito user pool ID. Needs to match the Florence one for the environment.                                                                                                                     |
| `AWS_COGNITO_APP_CLIENT_ID`        | The Cognito app client ID.                                                                                                                                                                         |
| `IDENTITY_API_BASE_URL`            | Used to fetch teams data.                                                                                                                                                                          |
| `SESSION_RENEWAL_OFFSET_SECONDS`   | The time offsets for session renewal. Defaults to 300 (5 minutes). Used by auth.js to pass to the [dis-authorisation-client-js](https://github.com/ONSdigital/dis-authorisation-client-js) library |

TODO: add details about the middleware, auth.js, ONSLogoutView and the team sync management command.

## Local testing

- [How to Integrate with existing Auth](https://confluence.ons.gov.uk/display/DIS/How+to+integrate+with+auth)
- [AWS Cognito Documentation](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools.html)
- [JWT](https://jwt.io/)

> [!NOTE]
>
> 1. When running the auth stub locally, you’ll need to access Wagtail through the proxy (stub url) provided by the stub. This is necessary due to how authentication works, specifically, browser security restrictions prevent cross-origin access to local storage, which the stub relies on. If you try to access Wagtail using the usual route (e.g. localhost:8000) while also logging in via the stub, you’ll be logged out automatically.
> 2. If you restart the stub, once Wagtail is already running, you must restart Wagtail as the JWK signing keys in Wagtail cache will not be in sync with the newly generated keys from the stub.
> 3. FYI, Cognito groups control both roles and preview teams. https://github.com/ONSdigital/dis-authentication-stub/blob/feature/fallback-to-wagtail/static/json/users.json#L7C5-L7C47 here, anything that is prefixed as `role-` are represented as Django User Groups and everything is a Preview Team (they are actually UUID in API response).

### Set up the authentication stub to mock Florence login flow.

1. Clone the stub: https://github.com/ONSdigital/dis-authentication-stub
2. Switch to branch `feature/fallback-to-wagtail`
3. Run the stub using `make debug`. You will need to have `go` installed.

### Run Wagtail

1. Take a DB snapshot on main branch so you can test other branches even after applying migrations in this. `poetry run dslr snapshot latest-main`.
2. Check out this branch
3. Run migrations via `make migrate`
4. Install node dependencies by running `npm install`, then `npm run build:prod `
5. OPTIONAL: Set the `WAGTAILADMIN_HOME_PATH = "wagtail-admin/"` in local.py if you want to mimic Florence redirect path name. However, for local development,, this is not important, and functionally, the auth stub has been updated to not care about the wagtail admin path. Note if you set this, make sure to update this string in any following instructions accordingly.
6. Sync Teams by running: `poetry run python ./manage.py sync_teams --settings=cms.settings.dev` (This will load some dummy preview teams). These can be found in [groups.json](https://github.com/ONSdigital/dis-authentication-stub/blob/feature/fallback-to-wagtail/static/json/groups.json).
7. Start Wagtail (`make compose dev-up`, `make run` - both from your host machine)
8. Go to http://localhost:29500/florence/login?redirect=http://localhost:29500/admin/ and log in as one of the users. You can see which roles/groups users have access to by looking at the [users.json](https://github.com/ONSdigital/dis-authentication-stub/blob/feature/fallback-to-wagtail/static/json/users.json).
9. Test various login and log-out flows and ensure everything is as expected.
10. Key things to test:

    - Log in with valid AWS Cognito tokens. The user should be authenticated and a session created.
    - Reload the page with valid tokens and a valid session. The middleware should let the request through without re-authenticating the user. Check the logs to verify the behaviour.
    - Try accessing the site with missing or expired tokens. The user should be logged out immediately.
    - Test what happens if only one of the tokens (access or ID) is present. The user should also be logged out in this case. After logging in, delete either the access or ID token manually in the browser. The user should be logged out on the next request.
    - Ensure that a Cognito user cannot log in using the default Wagtail login screen when Cognito login is enabled.
    - Set `WAGTAIL_CORE_ADMIN_LOGIN_ENABLED` to `False` and ensure the default Wagtail login is disabled.
    - On login, a user should be created/updated with their details (email, name, username) populated from the ID token.

    - Confirm that users are assigned the correct Django user group (e.g. Publishing Admins, Publishing Officers, Viewers) as per [users.json](https://github.com/ONSdigital/dis-authentication-stub/blob/feature/fallback-to-wagtail/static/json/users.json)
    - Check that users are added to the right preview teams as per [users.json](https://github.com/ONSdigital/dis-authentication-stub/blob/feature/fallback-to-wagtail/static/json/users.json)
    - Update the user’s group or team in [users.json](https://github.com/ONSdigital/dis-authentication-stub/blob/feature/fallback-to-wagtail/static/json/users.json), then log in again. The changes should be reflected in the user’s account on the next login.
    - Test session refresh behaviour near expiry. You can set `SESSION_RENEWAL_OFFSET_SECONDS` to `890` to force a refresh every 10 seconds and verify the logic works.
    - Check the console log to see that session management via JS is working as expected. (Read the https://github.com/ONSdigital/dis-authorisation-client-js README)
