Feature: Custom permissions for the CMS, independent of RBAC group permissions
    Background:
        Given a CMS user logs into the admin site

    Scenario: A CMS user is not able to create a Welsh page first
        Given the user navigates to the admin page navigator
        When the user navigates to the "Welsh" homepage in the page navigator
        Then the user has no option to create a child page

    Scenario: A CMS user is able to create an English page first
        Given the user navigates to the admin page navigator
        When the user navigates to the "English" homepage in the page navigator
        Then the user has the option to create a child page under the "Home" page

    Scenario: A CMS user has no option to copy a Welsh page
        Given a published information page exists
        And  a published information page translation exists
        When the user edits the welsh information page
        And  the user opens the page actions menu
        Then the user has no option to copy the page

    Scenario: A CMS user has the option to copy an English page
        Given an information page exists
        When the user edits the information page
        And  the user opens the page actions menu
        Then the user has the option to copy the page

    Scenario: A CMS user cannot modify the homepage
        Given the user navigates to the admin page navigator
        When the user navigates to the English home page in the Wagtail page explorer
        And the user opens the page actions menu
        And the user clicks the Edit menu item
        And the user opens the page actions menu
        Then the user cannot modify the page
