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

    # TODO: Write the step definitions and implementation for this scenario
    # Scenario: Duplicate topics are removed when creating an information page
    #     When the user creates an information page as a child of the home page
    #     And the user adds the same topic twice
    #     And the user saves the page
    #     Then only one instance of the topic is saved
