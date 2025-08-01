Feature: Simple JWT Authentication Test
    As an authenticated user
    I want to ensure that JWT-based authentication and session management work correctly
    So that I can securely access and manage the Wagtail admin interface

    @cognito_enabled
    Scenario: Session renewal fires on user activity
        Given I have valid JWT tokens and I set the authentication cookies
        When I navigate to the admin page
        And I perform an action that requires authentication such as mouse movements
        Then a session renewal request should be sent


    @cognito_enabled
    Scenario: Access Wagtail with valid JWT tokens
        Given I have valid JWT tokens and I set the authentication cookies
        When I navigate to the admin page
        Then I should not be redirected to the sign-in page

    @cognito_enabled
    Scenario: Block access with invalid JWT tokens
        Given I have no valid JWT tokens
        When I navigate to the admin page
        Then I should be redirected to the sign-in page


    @cognito_enabled
    Scenario: Automatic logout on token expiration
        Given I have valid JWT tokens and I set the authentication cookies
        When I navigate to the admin page
        And I remain inactive until my JWT token expires
        And I perform an action that requires authentication such as mouse movements
        Then I should be redirected to the sign-in page

    @cognito_enabled
    Scenario: Clear tokens on logout
        Given I have valid JWT tokens and I set the authentication cookies
        When I navigate to the admin page
        And I click the "Log out" button in the Wagtail UI
        Then the logout request should complete successfully
        And the tokens should be cleared from the browser

    @smoke
    @cognito_enabled
    Scenario: Keep multiple tabs in sync on token refresh or logout
        Given I have valid JWT tokens and I set the authentication cookies
        And I am logged in and have Wagtail open in two browser tabs
        When the JWT token is refreshed in one tab
        Then the second tab should update its session without a manual reload
        When I log out from one tab
        Then both tabs should be redirected to the sign-in page
        And no split session remains active
