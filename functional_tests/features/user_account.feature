Feature: A CMS user can view and edit their account details

    Background:
        Given a Publishing Admin logs into the admin site

    Scenario: A CMS user can view their account details
        When the user opens the account details page
        Then they can see their account details

    Scenario: A CMS user cannot edit their account details
        When the user opens the account details page
        Then they cannot edit their first name, last name or email

    Scenario: A CMS user can change their theme
        When the user opens the account details page
        And the user changes their theme to "Dark"
        And the user clicks "Save" to save the account details
        Then the user's theme is updated to "Dark"

    Scenario: A CMS user can change their notifications settings
        When the user opens the account details page
        And the user clicks on the Notifications tab
        And the user toggles Submitted notifications on
        And the user clicks "Save" to save the account details
        Then the user's Submitted notifications setting is updated to on
