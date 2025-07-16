Feature: UI Bundle Happy Paths
    """
    User Role Bundle Life Cycle Happy Path
                                | Search | Create | Edit | Preview | Approve
        Publishing Admin        |        | ok     |      |
            not in preview team | ToDo   | N/A    | ok   |
            in preview team     | ToDo   | N/A    | ok   |
        Publishing Officer      |        | ok     |
            not in preview team | ToDo   | N/A    | ok
            in preview team     | ToDo   | N/A    | ok
        Viewer                  |        | ok     |
            not in preview team | ToDo   | N/A    | N/A
            in preview team     | ToDo   | N/A    | N/A

    """


##---- Bundle Create UI Tests -----
#    Scenario Outline: A User can create a bundle
#        Given there is a <role> user
#        When the <role> logs in
#        Then the user can create a bundle
#        And the user goes to the bundle menu page
#        Examples: bundles
#           | role               |
#           | Publishing Admin   |
#           | Publishing Officer |
#
#
#    Scenario: A Viewer cannot create a bundle
#        Given there is a Viewer user
#        When the Viewer logs in
#        And the user goes to the bundle menu page
#        Then the user cannot create a bundle
#
##---- Bundle Edit UI Tests -----
    Scenario Outline: A User can edit a bundle with no preview teams and no release calendar
        Given there is a <role> user
        And there is a <creator_role> user
        And there are 1 Statistical Analysis pages
        And there are <Num_bundles> bundles created by <creator_role> with status <status>, Preview Teams <preview_teams>, Release Calendar <add_rel_cal>, Pages <add_stat_page>
        When the <role> logs in
        And the user goes to the bundle menu page
        Then the user can edit a bundle
        Examples: users
           | role               | Num_bundles | creator_role       | status | preview_teams | add_rel_cal | add_stat_page |
           | Publishing Admin   | 1           | Publishing Admin   | Draft  | False         |  False      | False         |
           | Publishing Officer | 1           | Publishing Officer | Draft  | False         |  False      | False         |
           | Publishing Admin   | 1           | Publishing Officer | Draft  | False         |  False      | False         |
           | Publishing Officer | 1           | Publishing Admin   | Draft  | False         |  False      | False         |

    Scenario Outline: A User can edit a bundle with preview teams but no membership and no release calendar
        Given there is a <role> user
        And there is a <creator_role> user
        And there are 1 Statistical Analysis pages
        And there are 1 Preview teams
        And there are <Num_bundles> bundles created by <creator_role> with status <status>, Preview Teams <preview_teams>, Release Calendar <add_rel_cal>, Pages <add_stat_page>
        When the <role> logs in
        And the user goes to the bundle menu page
        Then the user can edit a bundle
        Examples: users
           | role               | Num_bundles | creator_role       | status         | preview_teams |add_rel_cal | add_stat_page |
           | Publishing Admin   | 1           | Publishing Admin   | Draft          | True          | False      | False         |
           | Publishing Officer | 1           | Publishing Officer | Draft          | True          | False      | False         |
           | Publishing Admin   | 1           | Publishing Officer | Draft          | True          | False      | False         |
           | Publishing Officer | 1           | Publishing Admin   | Draft          | True          | False      | False         |

   Scenario Outline: A User can edit a bundle with preview teams without user membership and release calendar
        Given there is a <role> user
        And there is a <creator_role> user
        And there are 1 Statistical Analysis pages
        And there are 1 release calendar pages
        And there are 1 Preview teams
        And there are <Num_bundles> bundles created by <creator_role> with status <status>, Preview Teams <preview_teams>, Release Calendar <add_rel_cal>, Pages <add_stat_page>
        When the <role> logs in
        And the user goes to the bundle menu page
        Then the user can edit a bundle
        Examples: users
           | role               | Num_bundles | creator_role       | status         | preview_teams |add_rel_cal | add_stat_page |
           | Publishing Admin   | 1           | Publishing Admin   | Draft          | True          | False      | False         |
           | Publishing Officer | 1           | Publishing Officer | Draft          | True          | False      | False         |
           | Publishing Admin   | 1           | Publishing Officer | Draft          | True          | False      | False         |
           | Publishing Officer | 1           | Publishing Admin   | Draft          | True          | False      | False         |

    Scenario Outline: A User can edit a bundle with preview teams with user membership and release calendar
        Given there is a <role> user
        And there is a <creator_role> user
        And there are 1 Statistical Analysis pages
        And there are 1 release calendar pages
        And there are 1 Preview teams
        And the <role> is a member of the Preview teams
        And there are <Num_bundles> bundles created by <creator_role> with status <status>, Preview Teams <preview_teams>, Release Calendar <add_rel_cal>, Pages <add_stat_page>
        When the <role> logs in
        And the user goes to the bundle menu page
        Then the user can edit a bundle
        Examples: users
           | role               | Num_bundles | creator_role       | status         | preview_teams |add_rel_cal | add_stat_page |
           | Publishing Admin   | 1           | Publishing Admin   | Draft          | True          | False      | False         |
           | Publishing Officer | 1           | Publishing Officer | Draft          | True          | False      | False         |
           | Publishing Admin   | 1           | Publishing Officer | Draft          | True          | False      | False         |
           | Publishing Officer | 1           | Publishing Admin   | Draft          | True          | False      | False         |


#---- Bundle Preview UI Tests -----

  Scenario Outline: A User can preview a bundle without preview teams without user membership and release calendar
        Given there is a <role> user
        And there are 1 Statistical Analysis pages
        And there are <Num_bundles> bundles created by <creator_role> with status <status>, Preview Teams <preview_teams>, Release Calendar <add_rel_cal>, Pages <add_stat_page>
        When the <role> logs in
        And the user goes to the bundle menu page
        Then the user can preview a bundle
        Examples: users
           | role               | Num_bundles | creator_role       | status         | preview_teams |add_rel_cal | add_stat_page |
           | Publishing Admin   | 1           | Publishing Admin   | Draft          | False         | False      | False         |
           | Publishing Officer | 1           | Publishing Officer | Draft          | False         | False      | False         |
           | Publishing Admin   | 1           | Publishing Officer | Draft          | False         | False      | False         |
           | Publishing Officer | 1           | Publishing Admin   | Draft          | False         | False      | False         |
           | Viewer             | 1           | Publishing Admin   | Draft          | False         | False      | False         |
           | Viewer             | 1           | Publishing Officer | Draft          | False         | False      | False         |

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

