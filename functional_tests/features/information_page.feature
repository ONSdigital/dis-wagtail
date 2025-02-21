Feature: A general use information page

    Scenario: A CMS user can create and publish an information page
        Given a CMS user logs into the admin site
        When the user creates an information page as a child of the home page
        And the user adds content to the new information page
        And the user clicks publish page
        And the user clicks "View Live" on the publish confirmation banner
        Then the new information page with the added content is displayed
        And the user can see the breadcrumbs

    Scenario: Rich text toolbar is pinned by default
        Given a CMS user logs into the admin site
        When the user creates an information page as a child of the home page
        Then the rich text toolbar is displayed

    Scenario: Minimap is shown by default
        Given a CMS user logs into the admin site
        When the user creates an information page as a child of the home page
        Then the minimap is displayed
