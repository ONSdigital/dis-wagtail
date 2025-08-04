Feature: Wagtail Admin JWT Authentication and Session Management
    As an authenticated user
    I want to ensure that JWT-based authentication and session management work correctly
    So that I can securely access and manage the Wagtail admin interface

    @cognito_enabled
    Scenario: Session renewal fires on user activity
        Given I am authenticated
        When I navigate to the admin page
        And I am active in the admin interface
        Then a session renewal request should be sent

    @cognito_enabled
    Scenario: Access Wagtail with valid JWT tokens
        Given I am authenticated
        When I navigate to the admin page
        Then I should not be redirected to the sign-in page

    @cognito_enabled
    Scenario: Block access with invalid JWT tokens
        Given I have no valid JWT tokens
        When I navigate to the admin page
        Then I should be redirected to the sign-in page

    @cognito_enabled
    Scenario: Automatic logout on token expiration
        Given I am authenticated
        When I navigate to the admin page
        And I remain inactive for a period longer than the token's expiration time
        And I refresh the page
        Then I should be redirected to the sign-in page

    # This test will be failing in the near future where once the JWT token expires, the user will be redirected to the sign-in page when active again
    @cognito_enabled
    Scenario: No logout on token expiration
        Given I am authenticated
        When I navigate to the admin page
        And I remain inactive for a period longer than the token's expiration time
        And I become active again
        Then I should not be redirected to the sign-in page

    @cognito_enabled
    Scenario: Clear tokens on logout
        Given I am authenticated
        When I navigate to the admin page
        And I click the "Log out" button in the Wagtail UI
        Then the logout request should complete successfully
        And the tokens should be cleared from the browser

    @cognito_enabled
    Scenario: Keep multiple tabs in sync on token refresh or logout
        Given I am authenticated
        When I navigate to the admin page
        And I am logged in and open a second tab
        # When the JWT token is refreshed in one tab
        # Then the second tab should update its session without a manual reload
        When I log out from one tab
        Then both tabs should be redirected to the sign-in page

    @cognito_enabled
    Scenario: Ensure session is not initialised in the iframe
        Given I am authenticated
        When I am editing page
        Then I open the preview pane and the session should not be initialised in the iframe
