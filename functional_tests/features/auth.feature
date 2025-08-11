Feature: Wagtail Admin JWT Authentication and Session Management
    As an authenticated user
    I want to ensure that JWT-based authentication and session management work correctly
    So that I can securely access and manage the Wagtail admin interface

    @cognito_enabled
    Scenario: Session renewal fires on user activity
        Given the user is authenticated
        When the user navigates to the admin page
        And the user is active in the admin interface
        Then a session renewal request should be sent

    @cognito_enabled
    Scenario: Access Wagtail with valid JWT tokens
        Given the user is authenticated
        When the user navigates to the admin page
        Then the user should not be redirected to the sign-in page

    @cognito_enabled
    Scenario: Block access with invalid JWT tokens
        Given the user has no valid JWT tokens
        When the user navigates to the admin page
        Then the user should be redirected to the sign-in page

    @cognito_enabled
    Scenario: Automatic logout on token expiration
        Given the user is authenticated
        When the user navigates to the admin page
        And the user remains inactive for a period longer than the token's expiration time
        And the user refreshes the page
        Then the user should be redirected to the sign-in page

    # TODO: This test will need to be updated in the near future where once the JWT token expires, the user will be redirected to the sign-in page when active again
    @cognito_enabled
    Scenario: No logout on token expiration
        Given the user is authenticated
        When the user navigates to the admin page
        And the user remains inactive for a period longer than the token's expiration time
        And the user becomes active again
        Then the user should not be redirected to the sign-in page

    @cognito_enabled
    Scenario: Clear tokens on logout
        Given the user is authenticated
        When the user navigates to the admin page
        And the user clicks the "Log out" button in the Wagtail UI
        Then the logout request should complete successfully
        And the tokens should be cleared from the browser

    @smoke
    @cognito_enabled
    Scenario: Keep multiple tabs in sync on token refresh
        Given the user is authenticated
        When the user navigates to the admin page
        And the user opens a second tab
        When the JWT token is refreshed in one tab
        Then both tabs should remain logged in

    @cognito_enabled
    Scenario: Keep multiple tabs in sync on logout
        Given the user is authenticated
        When the user navigates to the admin page
        And the user opens a second tab
        When the user logs out from one tab
        Then both tabs should be redirected to the sign-in page

    @cognito_enabled
    Scenario: Ensure session is not initialised in the iframe
        Given the user is authenticated
        When the user navigates to the admin page
        And the user creates and saves an information page
        Then the user opens the preview pane and the session should not be initialised in the iframe
