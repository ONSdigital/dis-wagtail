Feature: auth.js integration on a real InformationPage

    Background:
        Given a superuser logs into the admin site
        And the user creates an information page as a child of the home page
        And the user adds content to the new information page
        And the user clicks "Publish"
        And the user clicks "View Live" on the publish confirmation banner
        And auth.js is initialised on the live page

    @keepalive
    Scenario: auth.js renews the Wagtail session from a real page
        When the passive renewal timer fires
        Then the browser must have made a POST request to "/admin/extend-session/"

    @preview_iframe
    Scenario: auth.js does not initialise inside preview iframe
        Given the user clicks "Preview" in the Wagtail editor
        Then auth.js is not initialised in the iframe
        And no network traffic occurs from the iframe
