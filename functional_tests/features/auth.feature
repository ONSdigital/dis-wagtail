@cognito_enabled
Feature: Wagtail Admin Cognito Authentication and Session Management
    As an authenticated user
    I want my session to behave predictably
    So that I can securely access and manage the Wagtail admin interface

    Scenario: Session extends when the user is active
        Given the user is authenticated
        When the user navigates to the admin page
        And the user is active in the admin interface
        Then their session is extended
        And the user remains logged in

    Scenario: Access Wagtail with a valid session
        Given the user is authenticated
        When the user navigates to the admin page
        Then the user is not asked to login

    Scenario: Redirect to login page when no valid session
        Given the user is unauthenticated
        When the user navigates to the admin page
        Then the user is redirected to the login page

    @short_expiry
    Scenario: User is logged out after session expiry
        Given the user is authenticated
        When the user navigates to the admin page
        And the user remains inactive until the session expires
        And the user refreshes the page
        Then the user is redirected to the login page

    # TODO: This test will need to be updated in the near future where once the JWT token expires, the user will be redirected to the sign-in page when active again
    @short_expiry
    Scenario: No logout on token expiration
        Given the user is authenticated
        When the user navigates to the admin page
        And the user remains inactive until the session expires
        And the user becomes active again
        Then their session is extended
        And the user is not asked to login

    Scenario: Logging out clears the session
        Given the user is authenticated
        When the user navigates to the admin page
        And the user clicks the "Log out" button in the Wagtail UI
        Then the user is logged out
        And all authentication data is cleared in the browser

    @long_expiry
    Scenario: Session refresh keeps multiple tabs logged in
        Given the user is authenticated
        When the user navigates to the admin page
        And the user opens an admin page in a second tab
        When the user interacts with the page in one tab
        Then both tabs should remain logged in

    @refresh_expiry
    @short_expiry
    Scenario: User is logged out when refresh token expires
        Given the user is authenticated
        When the user navigates to the admin page
        And the user remains inactive until the refresh token expires
        And the user becomes active again
        Then the user is redirected to the login page

    Scenario: Logging out in one tab logs out the others
        Given the user is authenticated
        When the user navigates to the admin page
        And the user opens an admin page in a second tab
        When the user logs out from one tab
        Then both tabs are redirected to the login page

    Scenario: Preview iframe does not start separate session management
        Given an information page exists
        And  the user is authenticated
        When the user edits the information page
        And  the user clicks toggle preview
        Then session management should not be initialised in the iframe
        And  the information page preview contains the populated data
