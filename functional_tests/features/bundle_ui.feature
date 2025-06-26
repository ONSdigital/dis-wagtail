Feature: UI Bundle Happy Paths

#---- Bundle Create UI Tests -----
    Scenario: A Publishing Admin creates a bundle
        Given there is a Publishing Admin user
        And there are 3 Preview teams
        And the user is a member of the Preview teams
        And there are 3 release calendar pages
        And there are 3 Statistical Analysis pages
        And there are 3 bundles
        When a Publishing Officer logs into the admin site
#        And the user can see the Bundles menu item
#        And the user clicks the Bundles menu item
#        Then the user can search for unknown bundle with response "There are no bundles to"
#        And the user can create a bundle
##
#    Scenario: A Publishing Officer creates a bundle
#        Given there is a Publishing Officer user
#        And there are 3 Preview teams
#        And the user is a member of the Preview teams
#        And there are 3 release calendar pages
#        And there are 3 Statistical Analysis pages
#        And there are 3 bundles
#        When the user logs in
#        And the user can see the Bundles menu item
#        And the user clicks the Bundles menu item
#        Then the user can search for unknown bundle with response "There are no bundles to"
#        And the user can create a bundle
##
#    Scenario: A Viewer not in preview groups cannot create a bundle
#        Given there is a Viewer user
#        And there are 3 Preview teams
#        And there are 3 release calendar pages
#        And there are 3 Statistical Analysis pages
#        And there are 3 bundles
#        When the user logs in
#        And the user can see the Bundles menu item
#        And the user clicks the Bundles menu item
#        Then the user can search for unknown bundle with response "There are no bundles to display."
#        And the user cannot create a bundle
##
#    Scenario: A Viewer in preview groups cannot create a bundle
#        Given there is a Viewer user
#        And there are 3 Preview teams
#        And the user is a member of the Preview teams
#        And there are 3 release calendar pages
#        And there are 3 Statistical Analysis pages
#        And there are 3 bundles
#        When the user logs in
#        And the user can see the Bundles menu item
#        And the user clicks the Bundles menu item
#        Then the user can search for unknown bundle with response "There are no bundles to"
#        And the user cannot create a bundle
#
##---- Bundle Edit  UI Tests -----
#    Scenario: A Publishing Admin edits bundle
#        Given there is a Publishing Admin user
#        And there are 3 Preview teams
#        And the user is a member of the Preview teams
#        And there are 3 release calendar pages
#        And there are 3 Statistical Analysis pages
#        And there are 3 bundles
#        When the user logs in
#        And the user can see the Bundles menu item
#        And the user clicks the Bundles menu item
#        Then the user can search for a known bundle
#        And the user edit edit the known bundle
#
#    Scenario: A Publishing Officer edits bundle
#        Given there is a Publishing Officer user
#        And there are 3 Preview teams
#        And the user is a member of the Preview teams
#        And there are 3 release calendar pages
#        And there are 3 Statistical Analysis pages
#        And there are 3 bundles
#        When the user logs in
#        And the user can see the Bundles menu item
#        And the user clicks the Bundles menu item
#        Then the user can search for a known bundle
#        And the user edit edit the known bundle
##
#    Scenario: A viewer edits bundle
#        Given there is a Publishing Admin user
#        And there are 3 Preview teams
#        And the user is a member of the Preview teams
#        And there are 3 release calendar pages
#        And there are 3 Statistical Analysis pages
#        And there are 3 bundles
#        When the user logs in
#        And the user can see the Bundles menu item
#        And the user clicks the Bundles menu item
#        Then the user can search for a known bundle
#        And the user cannot edit the known bundle
#
##---- Bundle Preview UI Tests -----
#
#
#---- Bundle Approve UI Tests -----
#---- Bundle Preview UI Tests -----
# ---- Bundle publish -----
#    Scenario: A Published bundle cannot be edited
#        Given there is a Publishing Admin user
#        And there are 3 Preview teams
#        And the Publishing Officer is a member of the Preview teams
#        And there are 3 release calendar pages
#        And there are 3 Statistical Analysis pages
#        And there are 3 bundles
#        When the user logs in
#        And the user can see the Bundles menu item
#        And the user clicks the Bundles menu item
#        Then the user can search for known bundle
#        And the user cannot edit a bundle
