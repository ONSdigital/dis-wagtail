Feature: A general use information page

    Scenario: A CMS user can create and publish an information page
        Given a CMS user logs into the admin site
        When the user navigates to the pages menu
        And the user clicks add child page and chooses information page type
        And the user adds content to the new information page
        And the user clicks "Publish page"
        And the user clicks "View Live" on the publish confirmation banner
        Then the new information page with the added content is displayed
        And the user can see the breadcrumbs

