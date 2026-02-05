Feature: A general use information page

    Background:
        Given a superuser logs into the admin site

    Scenario: A CMS user can create an information page
        When the user creates an information page as a child of the home page
        And  the user adds content to the new information page
        Then the user can create the page
        When the user opens the preview in a new tab
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

    Scenario: The CMS user can see the date placeholder in the date field of the information page
        When the user creates an information page as a child of the home page
        Then the date placeholder "YYYY-MM-DD" is displayed in the "Last updated" textbox
