Feature: Role Based Access Control Permission as defined in data migrations

    # Publishing Admin
    Scenario: A Publishing Admin can see the Reports menu item
        When a Publishing Admin logs into the admin site
        Then the user can see the Reports menu item

    Scenario: A Publishing Admin can create and publish pages
        When a Publishing Admin logs into the admin site
        Then the user can see the Pages menu item
        And the user creates an information page as a child of the index page
        And the user can save a draft version of the page
        And the user can publish a page

    Scenario: A Publishing Admin can bulk delete pages
        Given a topic page exists under the homepage
        And a statistical article page has been published under the topic page
        When a Publishing Admin logs into the admin site
        Then the user can bulk delete the topic page and its children

    Scenario: A Publishing Admin can lock and unlock a page
        Given a statistical article exists 
        And a Publishing Admin logs into the admin site
        And the user can see the Pages menu item
        When the user edits the statistical article page
        Then the user can lock and unlock a page

    Scenario: A Publishing Admin can manage image collections
        When a Publishing Admin logs into the admin site
        Then the user can see the Images menu item

    Scenario: A Publishing Admin can manage document collections
        When a Publishing Admin logs into the admin site
        Then the user can see the Documents menu item

    Scenario: A Publishing Admin can view Preview teams
        When a Publishing Admin logs into the admin site
        Then the user can see the Preview teams menu item

    Scenario: A Publishing Admin can manage Wagtail settings
        When a Publishing Admin logs into the admin site
        And the user can see the Settings menu item
        And the user clicks the Settings menu item
        And the user can see the Navigation settings menu item
        And the user can see the Social media settings menu item

    Scenario: A Publishing Admin can manage Definitions
        Given a Publishing Admin logs into the admin site
        And the user can see the Snippets menu item
        When the user clicks the Snippets menu item
        Then the user can add Definitions snippet

    Scenario: A Publishing Admin can manage Contact Details
        Given a Publishing Admin logs into the admin site
        And the user can see the Snippets menu item
        When the user clicks the Snippets menu item
        Then the user can add Contact details snippet

    Scenario: A Publishing Admin can manage and publish Main Menu
        Given a Publishing Admin logs into the admin site
        And the user can see the Snippets menu item
        When the user clicks the Snippets menu item
        Then the user can create and publish the Main menus snippet

    Scenario: A Publishing Admin can manage and publish Footer Menu
        Given a Publishing Admin logs into the admin site
        And the user can see the Snippets menu item
        When the user clicks the Snippets menu item
        Then the user can create and publish the Footer menus snippet

    Scenario: A Publishing Admin can add Bundles
        Given a Publishing Admin logs into the admin site
        And the user can see the Bundles menu item
        When the user clicks the Bundles menu item
        Then the user can add Bundles

    # Publishing Officer

    Scenario: A Publishing Officer can create pages
        When a Publishing Officer logs into the admin site
        Then the user can see the Pages menu item
        And the user creates a draft information page as a child of the index page
        And the user adds content to the new information page
        And the user can save a draft version of the page

    Scenario: A Publishing Officer can add Bundles
        Given a Publishing Officer logs into the admin site
        And the user can see the Bundles menu item
        When the user clicks the Bundles menu item
        Then the user can add Bundles

    Scenario: A Publishing Officer can view Preview teams
        When a Publishing Officer logs into the admin site
        Then the user can see the Preview teams menu item

    Scenario: A Publishing Officer cannot change a published notice
        Given a Release Calendar page with a published notice exists
        Given a Publishing Officer logs into the admin site
        When the user navigates to the published release calendar page
        Then the notice field is disabled

    # Viewer

    Scenario: A Viewer can inspect Bundles details
        Given a bundle has been created
        And is ready for review
        And has a preview team
        When a Viewer logs into the admin site
        And the viewer is in the preview team
        Then the user can see the Bundles menu item
        And the user can inspect bundle details
