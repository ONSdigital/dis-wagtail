Feature: A general use information page

    Background:
        Given a superuser logs into the admin site

    Scenario: A CMS user can create and publish an information page
        When the user creates an information page as a child of the home page
        And the user adds content to the new information page
        And the user clicks "Publish"
        And the user clicks "View Live" on the publish confirmation banner
        Then the new information page with the added content is displayed
        And the user can see the breadcrumbs

    Scenario: Rich text toolbar is pinned by default
        When the user creates an information page as a child of the home page
        Then the rich text toolbar is pinned

    Scenario: The CMS user unpins the rich text toolbar and the preference is saved
        And the user creates an information page as a child of the home page
        And the rich text toolbar is pinned
        When the user unpins the rich text toolbar
        And the user refreshes the page
        Then the rich text toolbar is unpinned

    Scenario: Minimap is shown by default
        When the user creates an information page as a child of the home page
        Then the minimap is displayed

    Scenario: The CMS user hides the minimap and the preference is saved
        And the user creates an information page as a child of the home page
        And the minimap is displayed
        When the user hides the minimap
        And the user refreshes the page
        Then the minimap is hidden

    # TODO: This test needs updating once the regressed de-duplication for taxonomy topics is fixed
    # TODO: Update the last Then step to check that no duplicate topics are shown once fixed
    Scenario: Duplicate topics are removed when creating an information page
        Given the following taxonomy topics exist:
                | topic     |
                | Economy   |
                | Inflation |
                | CPI       |
        When the user creates an information page as a child of the home page
        And the user adds content to the new information page
        And the user adds the taxonomy topic "Inflation" twice
        And the user clicks the "Save Draft" button
        Then the duplicate topic error message is shown

    Scenario: Index page lists child information pages alphabetically
        Given the index page has the following information pages:
            | page_name       | live  |
            | Zebra Info      | true  |
            | Alpha Info      | true  |
            | Draft Only Info | false |
            | Beta Info       | true  |
        When the user visits the live index page
        Then the live index page lists only live information pages in alphabetical order
        When the user visits the index page preview
        Then the index page preview lists live and draft information pages in alphabetical order
