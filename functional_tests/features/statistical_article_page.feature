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
        And the user clicks "Publish page"
        And the user returns to editing the statistical article page
        And the user adds a correction
        And the user clicks "Publish page"
        And the user clicks "View Live" on the publish confirmation banner
        Then the published statistical article page has the added correction

    Scenario: A CMS user can edit a correction to a Statistical Article Page
        Given a CMS user logs into the admin site
        When the user goes to add a new statistical article page
        And the user adds basic statistical article page content
        And the user clicks "Publish page"
        And the user returns to editing the statistical article page
        And the user adds a correction
        And the user clicks "Publish page"
        And the user returns to editing the statistical article page
        Then the user can edit the correction

      Scenario: A CMS user cannot delete a correction to a Statistical Article Page once it is published
        Given a CMS user logs into the admin site
        When the user goes to add a new statistical article page
        And the user adds basic statistical article page content
        And the user clicks "Publish page"
        And the user returns to editing the statistical article page
        And the user adds a correction
        And the user clicks "Publish page"
        And the user returns to editing the statistical article page
        Then the user cannot delete the correction

    Scenario: A CMS user can view a superseeded Statistical Article Page
        Given a CMS user logs into the admin site
        When the user goes to add a new statistical article page
        And the user adds basic statistical article page content
        And the user clicks "Publish page"
        And the user returns to editing the statistical article page
        And the user updates the statistical article page content
        And the user adds a correction
        And the user clicks "Publish page"
        And the user clicks "View Live" on the publish confirmation banner
        And the user clicks on "View superseded version"
        Then the user can view the superseeded statistical article page

    Scenario: A CMS user can add a notice to a Statistical Article Page
        Given a CMS user logs into the admin site
        When the user goes to add a new statistical article page
        And the user adds basic statistical article page content
        And the user adds a notice
        And the user clicks "Publish page"
        And the user clicks "View Live" on the publish confirmation banner
        Then the published statistical article page has the added notice
