Feature: Statistical Article Page components

    Scenario: A CMS user can create and publish a Statistical Article Page
        Given a CMS user logs into the admin site
        When the user goes to add a new statistical article page
        And the user adds basic statistical article page content
        And the user clicks "Publish page"
        And the user clicks "View Live" on the publish confirmation banner
        Then the published statistical article page is displayed with the populated data


    Scenario: A CMS user can add a table a Statistical Article Page
        Given a CMS user logs into the admin site
        When the user goes to add a new statistical article page
        And the user adds basic statistical article page content
        And the user adds a table with pasted content
        And the user clicks "Publish page"
        And the user clicks "View Live" on the publish confirmation banner
        Then the published statistical article page is displayed with the populated data
        And the published statistical article page has the added table
        And the user can expand the footnotes

    Scenario: A CMS user can add a correction to a Statistical Article Page
        Given a CMS user logs into the admin site
        When the user goes to add a new statistical article page
        And the user adds basic statistical article page content
        And the user clicks the "Save Draft" button
        And the user adds a correction
        And the user clicks "Publish page"
        And the user clicks "View Live" on the publish confirmation banner
        Then the published statistical article page has the added correction

    Scenario: A CMS user can add a notice to a Statistical Article Page
        Given a CMS user logs into the admin site
        When the user goes to add a new statistical article page
        And the user adds basic statistical article page content
        And the user clicks the "Save Draft" button
        And the user adds a notice
        And the user clicks "Publish page"
        And the user clicks "View Live" on the publish confirmation banner
        Then the published statistical article page has the added notice
