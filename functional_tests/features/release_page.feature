Feature: CMS users can draft, edit, and publish release pages

    Scenario: A CMS user can author a provisional release page
        Given a contact details snippet exists
        And a CMS user logs into the admin site
        When the user navigates to the release calendar page
        And clicks "add child page" to create a new draft release page
        And the user sets the page status to "Published"
        And enters some example content on the page
        And the user clicks publish page
        And the user clicks "View Live" on the publish confirmation banner
        Then the new published release page with the example content is displayed
        And the user can see the breadcrumbs
