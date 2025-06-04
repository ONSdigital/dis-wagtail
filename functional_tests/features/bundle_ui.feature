Feature: UI Bundle Happy Path

    Background:
#        Setting up the require data to be used by this testing created using factory as this is not part of the UI testing
        Given there is a Preview teams and viewer is a member of these teams
        And there are 3 release calendar pages
        And there are 6 Statistical Analysis pages

    Scenario: A Publishing Admin Should see the Preview team
        When a Publishing Admin logs into the admin site
        And the user can see the Preview teams menu item
        And the user clicks the Preview teams menu item

    Scenario: A Publishing Officer Should not see the Preview team
        When a Publishing Officer logs into the admin site
        And the user can see the Preview teams menu item
        And the user clicks the Preview teams menu item

    Scenario: A viewer Officer Should not see the Preview team
        When a Viewer logs into the admin site
        And the user can see the Preview teams menu item
        And the user clicks the Preview teams menu item


    Scenario: A Publishing Admin Should see the Bundles Menu
        When a Publishing Admin logs into the admin site
        And the user can see the Bundles menu item
        And the user clicks the Bundles menu item

    Scenario: A Publishing Officer Should see the Bundles Menu
        When a Publishing Officer logs into the admin site
        And the user can see the Bundles menu item
        And the user clicks the Bundles menu item

    Scenario: A Viewer Should see the Bundles Menu
        When a Viewer logs into the admin site
        And the user can see the Bundles menu item
        And the user clicks the Bundles menu item
