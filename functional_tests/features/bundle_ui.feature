Feature: UI Bundle Happy Path

    Background:
#        Setting up the require data to be used by this testing created using factory as this is not part of the UI testing
        Given there are 3 Preview teams and viewer is a member of these teams
        And there are 3 release calendar pages
        And there are 3 Statistical Analysis pages

    Scenario: A Publishing Admin Should see the Bundles Menu and add bundle
        When a Publishing Admin logs into the admin site
        And the user can see the Bundles menu item
        And the user clicks the Bundles menu item
        Then the user can add Bundles
        And the user completes the Bundle details

    Scenario: A Publishing Officer Should see the Bundles Menu and add bundle
        When a Publishing Officer logs into the admin site
        And the user can see the Bundles menu item
        And the user clicks the Bundles menu item
        Then the user can add Bundles


    Scenario: A Viewer Should see the Bundles Menu but not add bundle
        When a Viewer logs into the admin site
        And the user can see the Bundles menu item
        And the user clicks the Bundles menu item
        Then the user can not add Bundles

