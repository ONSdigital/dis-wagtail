Feature: Statistical Article Page components

    Background:
        Given a superuser logs into the admin site

    Scenario: A CMS user can create and publish a Statistical Article Page
        When the user goes to add a new statistical article page
        And the user adds basic statistical article page content
        And the user clicks "Publish"
        And the user clicks "View Live" on the publish confirmation banner
        Then the published statistical article page is displayed with the populated data


    Scenario: A CMS user can add a table on a Statistical Article Page
        When the user goes to add a new statistical article page
        And the user adds basic statistical article page content
        And the user adds a table with pasted content
        And the user clicks "Publish"
        And the user clicks "View Live" on the publish confirmation banner
        Then the published statistical article page is displayed with the populated data
        And the published statistical article page has the added table
        And the user can expand the footnotes

    Scenario: A CMS user can add a correction to a Statistical Article Page
        When the user goes to add a new statistical article page
        And the user adds basic statistical article page content
        And the user clicks "Publish"
        And the user returns to editing the statistical article page
        And the user adds a correction
        And the user clicks "Publish"
        And the user clicks "View Live" on the publish confirmation banner
        Then the published statistical article page has the added correction
        And the user can expand and collapse correction details

    Scenario: A CMS user can edit a correction to a Statistical Article Page
        When the user goes to add a new statistical article page
        And the user adds basic statistical article page content
        And the user clicks "Publish"
        And the user returns to editing the statistical article page
        And the user adds a correction
        And the user clicks "Publish"
        And the user returns to editing the statistical article page
        Then the user can edit the correction

    Scenario: A CMS user cannot delete a correction to a Statistical Article Page once it is published
        When the user goes to add a new statistical article page
        And the user adds basic statistical article page content
        And the user clicks "Publish"
        And the user returns to editing the statistical article page
        And the user adds a correction
        And the user clicks "Publish"
        And the user returns to editing the statistical article page
        Then the user cannot delete the correction

    Scenario: Corrections are saved in chronological order
        When the user goes to add a new statistical article page
        And the user adds basic statistical article page content
        And the user clicks "Publish"
        And the user returns to editing the statistical article page
        And the user adds a correction
        And the user clicks "Publish"
        And the user returns to editing the statistical article page
        And the user adds another correction using the add button at the bottom
        And the user clicks "Publish"
        And the user clicks "View Live" on the publish confirmation banner
        Then the published statistical article page has corrections in chronological order

    Scenario: A CMS user can view a superseded Statistical Article Page
        When the user goes to add a new statistical article page
        And the user adds basic statistical article page content
        And the user clicks "Publish"
        And the user returns to editing the statistical article page
        And the user updates the statistical article page content
        And the user adds a correction
        And the user clicks "Publish"
        And the user clicks "View Live" on the publish confirmation banner
        And the user clicks on "View superseded version"
        Then the user can view the superseded statistical article page

    Scenario: A CMS user can add a notice to a Statistical Article Page
        When the user goes to add a new statistical article page
        And the user adds basic statistical article page content
        And the user adds a notice
        And the user clicks "Publish"
        And the user clicks "View Live" on the publish confirmation banner
        Then the published statistical article page has the added notice
        And the user can expand and collapse notice details

    Scenario: A CMS user can add a correction and a notice to a Statistical Article Page
        When the user goes to add a new statistical article page
        And the user adds basic statistical article page content
        And the user clicks "Publish"
        And the user returns to editing the statistical article page
        And the user adds a correction
        And the user adds a notice
        And the user clicks "Publish"
        And the user clicks "View Live" on the publish confirmation banner
        Then the published statistical article page has the corrections and notices block
        And the user can click on "Show detail" to expand the corrections and notices block
        And the user can click on "Close detail" to collapse the corrections and notices block

    Scenario: A CMS user can add headline figures to a Statistical Article Page
        When the user goes to add a new statistical article page
        And the user adds basic statistical article page content
        And the user adds headline figures
        And the user clicks "Publish"
        And the user clicks "View Live" on the publish confirmation banner
        Then the published statistical article page has the added headline figures
        
    Scenario: A CMS user can see date placeholders on a Statistical Article Page by textbox
        When the user goes to add a new statistical article page
        Then the date placeholder "YYYY-MM-DD" is displayed in the "Release date*" textbox
        And the date placeholder "YYYY-MM-DD" is displayed in the "Next release date" textbox
