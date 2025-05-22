Feature: JavaScript disabled fallbacks

    @no_javascript
    Scenario: The fallback equation on a Statistical Article is visible to non-JS users
        Given the user has JavaScript disabled
        And a statistical article page with equations exists
        Then the user can see the equation fallback

    Scenario: The fallback equation on a Statistical Article is not visible to non-JS users
        Given the user has JavaScript enabled
        Given a statistical article page with equations exists
        Then the user cannot see the equation fallback
