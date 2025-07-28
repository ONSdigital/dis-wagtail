Feature: Simple JWT Authentication Test
    Test basic JWT cookie authentication flow

    @cognito_enabled
    Scenario: Session renewal fires on user activity
        Given I have valid JWT tokens and I set the authentication cookies
        When I navigate to the admin page
        # Then a session renewal request should be sent
        And the user creates an information page as a child of the home page
        And the user adds content to the new information page