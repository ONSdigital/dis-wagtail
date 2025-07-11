Feature: UI Bundle Happy Paths
    """
    User Role Bundle Life Cycle Happy Path
                                | Create | Preview | Edit | Preview | Approve | Preview | Publish
        Publishing Admin        |
            not in preview team |
            in preview team     |
        Publishing Officer      |
            not in preview team |
            in preview team     |
        Viewer                  |
                        not in preview team |
            in preview team     |

    User Role
        Publishing Admin, in preview team, not in preview team, bundle creator, not bundle creator
        Publishing Officer in preview team, not in preview team bundle creator, not bundle creator
        Viewer in preview team, not in preview team
    """


#---- Bundle Create UI Tests -----
    Scenario: A Publishing Admin creates a bundle
        Given there is a Publishing Admin user
        And there is a Viewer user
        And there are 3 Preview teams
        And the Viewer is a member of the Preview teams
        And there are 3 release calendar pages
        And there are 3 Statistical Analysis pages
        And there are 3 bundles
        When the Publishing Admin logs in
#        And the user can see the Bundles menu item
#        And the user clicks the Bundles menu item
#        Then the user can search for unknown bundle with response "There are no bundles to"
#        And the user can create a bundle
#
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
#
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
#
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
#        And the user can edit the known bundle
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
#        And the user can edit the known bundle
##
#    Scenario: A viewer cannot edit a bundle
#        Given there is a Viewer user
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
#    Scenario: A Publishing Admin can preview the known bundle
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
#        And the user can preview the known bundle
#
#    Scenario: A Publishing Officer can preview the known bundle
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
#        And the user can preview the known bundle
#
#Scenario: A viewer in the preview group can preview the known bundle
#        Given there is a Viewer user
#        And there are 3 Preview teams
#        And the user is a member of the Preview teams
#        And there are 3 release calendar pages
#        And there are 3 Statistical Analysis pages
#        And there are 3 bundles
#        When the user logs in
#        And the user can see the Bundles menu item
#        And the user clicks the Bundles menu item
#        Then the user can search for a known bundle
#        And the user can preview the known bundle
#
#    Scenario: A viewer not in the preview group cannot preview the known bundle
#        Given there is a Viewer user
#        And there are 3 Preview teams
#        And the user is a member of the Preview teams
#        And there are 3 release calendar pages
#        And there are 3 Statistical Analysis pages
#        And there are 3 bundles
#        When the user logs in
#        And the user can see the Bundles menu item
#        And the user clicks the Bundles menu item
#        Then the user can search for a known bundle
#        And the user cannot preview the known bundle
#
#
##---- Bundle Approve UI Tests -----
#    Scenario: A Publishing Admin as the creator of the known bundle cannot approve known bundle
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
#        And the user cannot approve the known bundle
#
#    Scenario: A Publishing Officer as the creator of the known bundle cannot approve known bundle
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
#        And the user can approve the known bundle
#
#    Scenario: A Publishing Admin not as the creator of the known bundle can approve known bundle
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
#        And the user cannot approve the known bundle
#
#    Scenario: A Publishing Officer not as the creator of the known bundle can approve known bundle
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
#        And the user can approve the known bundle
#
#    Scenario: A Viewer cannot approve known bundle
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
#        And the user cannot approve the known bundle
#
##---- Bundle Preview UI Tests -----
#  Scenario: A Publishing Admin can preview the known bundle
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
#        And the user can preview the known bundle
#
#    Scenario: A Publishing Officer can preview the known bundle
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
#        And the user can preview the known bundle
#
#Scenario: A viewer in the preview group can preview the known bundle
#        Given there is a Viewer user
#        And there are 3 Preview teams
#        And the user is a member of the Preview teams
#        And there are 3 release calendar pages
#        And there are 3 Statistical Analysis pages
#        And there are 3 bundles
#        When the user logs in
#        And the user can see the Bundles menu item
#        And the user clicks the Bundles menu item
#        Then the user can search for a known bundle
#        And the user can preview the known bundle
#
#    Scenario: A viewer not in the preview group cannot preview the known bundle
#        Given there is a Viewer user
#        And there are 3 Preview teams
#        And the user is a member of the Preview teams
#        And there are 3 release calendar pages
#        And there are 3 Statistical Analysis pages
#        And there are 3 bundles
#        When the user logs in
#        And the user can see the Bundles menu item
#        And the user clicks the Bundles menu item
#        Then the user can search for a known bundle
#        And the user cannot preview the known bundle

