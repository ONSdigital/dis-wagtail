Feature: auth.js integration on a InformationPage

    Background:
        Given a superuser logs into the admin site
        And the user creates an information page as a child of the home page
        And the user adds content to the new information page
        And auth.js is initialised on the live page

    @cognito_enabled
    Scenario: auth.js data-island is injected into the live page
        When the user clicks "Publish"
        And the user clicks "View Live" on the publish confirmation banner
        Then the live page should include a `<script id="auth-config">` data-island
        And the live page should load `/static/js/auth.js`

    @smoke
    @cognito_enabled
    Scenario: auth.js renews the Wagtail session via passive timer
        When the user clicks "Publish"
        And the user clicks "View Live" on the publish confirmation banner
        And the passive renewal timer fires
        Then the browser must have made a POST request to "/admin/extend-session/"
        And that request must include the CSRF header "X-CSRFTOKEN"

    @cognito_enabled
    Scenario: auth.js does not initialise inside preview iframe
        When the user clicks the "Preview" button
        Then auth.js should not be initialised in the iframe
        And no network traffic should occur within the iframe
