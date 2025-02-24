Feature: A general use information page

    Scenario: A CMS user can create and publish an information page
        Given a CMS user logs into the admin site
        When the user creates an information page as a child of the home page
        And the user adds content to the new information page
        And the user clicks "Publish page"
        And the user clicks "View Live" on the publish confirmation banner
        Then the new information page with the added content is displayed
        And the user can see the breadcrumbs

    Scenario: Rich text toolbar is pinned by default
        Given a CMS user logs into the admin site
        When the user creates an information page as a child of the home page
        Then the rich text toolbar is pinned

    Scenario: Rich text toolbar selection is being saved
        Given a CMS user logs into the admin site
        And the user creates an information page as a child of the home page
        And the rich text toolbar is pinned
        When the user unpins the rich text toolbar
        And the user refreshes the page
        Then the rich text toolbar is unpinned

    Scenario: Minimap is shown by default
        Given a CMS user logs into the admin site
        When the user creates an information page as a child of the home page
        Then the minimap is displayed

    Scenario: Minimap selection is being saved
        Given a CMS user logs into the admin site
        And the user creates an information page as a child of the home page
        And the minimap is displayed
        When the user hides the minimap
        And the user refreshes the page
        Then the minimap is hidden