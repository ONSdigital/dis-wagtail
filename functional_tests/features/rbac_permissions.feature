Feature: Role Based Access Control Permission as defined in data migrations

    # Publishing Admin
    Scenario: A Publishing Admin can see the Reports menu item
        When a Publishing Admin logs into the admin site
        Then the user can see the Reports menu item

    Scenario: A Publishing Admin can create and publish pages
        When a Publishing Admin logs into the admin site
        Then the user can see the Pages menu item
        And the user can create and publish a page

    # TODO - Other page permissions from: WAGTAIL_PAGE_PERMISSION_TYPES = ["add", "change", "bulk_delete", "lock", "publish", "unlock"]

    Scenario: A Publishing Admin can manage image collections
        When a Publishing Admin logs into the admin site
        Then the user can see the Images menu item

    Scenario: A Publishing Admin can manage Glossary Terms
        Given a Publishing Admin logs into the admin site
        And the user can see the Snippets menu item
        When the user navigates to the Snippets admin page
        Then the user can add Glossary terms snippet
    
    Scenario: A Publishing Admin can manage Contact Details
        Given a Publishing Admin logs into the admin site
        And the user can see the Snippets menu item
        When the user navigates to the Snippets admin page
        Then the user can add Contact details snippet

    Scenario: A Publishing Admin can manage and publish Main Menu
        Given a Publishing Admin logs into the admin site
        And the user can see the Snippets menu item
        When the user navigates to the Snippets admin page
        Then the user can create and publish the Main menus snippet

    Scenario: A Publishing Admin can manage and publish Footer Menu
        Given a Publishing Admin logs into the admin site
        And the user can see the Snippets menu item
        When the user navigates to the Snippets admin page
        Then the user can create and publish the Footer menus snippet

    Scenario: A Publishing Admin can manage Bundles
        Given a Publishing Admin logs into the admin site 
        And the user can see the Bundles menu item
        When the user navigates to the Bundles admin page
        Then the user can add Bundles
        

    # Publishing Officer
    Scenario: A Publishing Officer can create pages
        When a Publishing Officer logs into the admin site
        Then the user can see the Pages menu item
        And the user can create and save a page

    Scenario: A Publishing Officer can manage Bundles
        Given a Publishing Officer logs into the admin site
        And the user can see the Bundles menu item
        When the user navigates to the Bundles admin page
        Then the user can add Bundles

    # Viewer

    Scenario: A Viewer can see Bundles
        Given a Viewer logs into the admin site
        And the user can see the Bundles menu item

