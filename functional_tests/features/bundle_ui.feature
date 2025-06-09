Feature: UI Bundle Happy Paths

    Scenario: A Publishing Admin Add New bundle Test_01
        Given there are 3 Preview teams and viewer is a member of these teams
        And there are 3 release calendar pages
        And there are 3 Statistical Analysis pages
        And there are 1 bundles
        When a Publishing Admin logs into the admin site
        And the user can see the Bundles menu item
        And the user clicks the Bundles menu item
        And the user can search for known bundle name Test_01
        Then the user can add Bundles
        And the user completes the Bundle details Test_01
#
#    Scenario: A Publishing Officer Should see the Bundles Menu and add bundle
#        When a Publishing Officer logs into the admin site
#        And the user can see the Bundles menu item
#        And the user clicks the Bundles menu item
#        And the user can search
#        And the user can search for Test_01
#        And the user can search filter draft
#        And the user can search filter In Preview
#        And the user can search filter In Preview
#
#        Then the user can add Bundles
#        And the user can search for Test_01
#        And the user completes the Bundle details Test_01
#        And the user can search for Test_01
#
#
#    Scenario: A Viewer Should see the Bundles Menu but not add bundle
#        When a Viewer logs into the admin site
#        And the user can see the Bundles menu item
#        And the user clicks the Bundles menu item
#        Then the user can not add Bundles

