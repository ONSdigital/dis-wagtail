Feature: UI Bundle Happy Paths
    """
    User Role Bundle Life Cycle Happy Path
                                 | Search | Create | Edit | Preview | Approve |
        Publishing Admin         | ToDo   | Can    | Can  | Can     | N/A     |
            As Creator of Bundle | N/A    | N/A    | N/A  | N/A     | Cannot  |
            Not Creator          | N/A    | N/A    | N/A  | N/A     | Can     |
        Publishing Officer       | ToDo   | Can    | Can  | Can     | N/A     |
            As Creator of Bundle | N/A    | N/A    | N/A  | N/A     | Cannot  |
            Not Creator          | N/A    | N/A    | N/A  | N/A     | Can     |
        Viewer                   | N/A    | Cannot | N/A  | N/A     | N/A     |
            not in preview team  | ToDo   | N/A    | N/A  | Cannot  | N/A     |
            in preview team      | ToDo   | N/A    | N/A  | Can     | N/A     |

    """
#---- Bundle Create UI Tests -----
    Scenario Outline: A User can create a bundle
        Given there is a <role> user
        When the <role> logs in
        Then the user can create a bundle

        Examples: bundles
           | role               |
           | Publishing Admin   |
           | Publishing Officer |


    Scenario Outline: A User cannot create a bundle
        Given there is a <role> user
        When the <role> logs in
        Then the user cannot create a bundle

        Examples: bundles
           | role     |
           | Viewer   |

#---- Bundle Edit UI Tests -----

    Scenario Outline: A User can edit a bundle
        Given there is a <role> user
        And there is a <creator_role> user
        And there are 1 Statistical Analysis pages
        And there are 1 release calendar pages
        And there are 1 Preview teams
        And the <role> is a member of the Preview teams
        And there are <Num_bundles> bundles created by <creator_role> with status <status> Preview Teams <preview_teams> Release Calendar <add_rel_cal>, Pages <add_stat_page>
        When the <role> logs in
        And the user goes to the bundle menu page
        Then the user can edit a bundle

        Examples: bundles
           | role               | Num_bundles | creator_role       | status         | preview_teams |add_rel_cal | add_stat_page |
           | Publishing Admin   | 1           | Publishing Admin   | Draft          | False         | False      | False         |
           | Publishing Officer | 1           | Publishing Officer | Draft          | False         | False      | False         |
           | Publishing Admin   | 1           | Publishing Officer | Draft          | False         | False      | False         |
           | Publishing Officer | 1           | Publishing Admin   | Draft          | False         | False      | False         |


#---- Bundle Preview UI Tests -----

  Scenario Outline: A User can preview a bundle
        Given there is a <role> user
        And there is a <creator_role> user
        And there are 1 Statistical Analysis pages
        And there are 1 release calendar pages
        And there are 1 Preview teams
        And the <role> is a member of the Preview teams
        And there are <Num_bundles> bundles created by <creator_role> with status <status> Preview Teams <preview_teams>, Release Calendar <add_rel_cal>, Pages <add_stat_page>
        When the <role> logs in
        Then the <role> can preview a bundle

        Examples: bundles
           | role               | Num_bundles | creator_role       | status         | preview_teams |add_rel_cal | add_stat_page |
           | Publishing Admin   | 1           | Publishing Admin   | In_Review      | True          | True       | True          |
           | Publishing Officer | 1           | Publishing Admin   | In_Review      | True          | True       | True          |
           | Viewer             | 1           | Publishing Admin   | In_Review      | True          | True       | True          |

      Scenario Outline: A User cannot preview a bundle
        Given there is a <role> user
        And there are 1 Statistical Analysis pages
        And there are 1 release calendar pages
        And there are 1 Preview teams
        And there are <Num_bundles> bundles created by <creator_role> with status <status>, Preview Teams <preview_teams>, Release Calendar <add_rel_cal>, Pages <add_stat_page>
        When the <role> logs in
        Then the <role> cannot preview a bundle

        Examples: bundles
           | role               | Num_bundles | creator_role       | status         | preview_teams |add_rel_cal | add_stat_page |
           | Viewer             | 1           | Publishing Admin   | In_Review      | False         | True       | True          |


      Scenario Outline: A user can approve known bundle
        Given there is a <role> user
        And there are 1 Statistical Analysis pages
        And there are 1 release calendar pages
        And there are 1 Preview teams
        And the <role> is a member of the Preview teams
        And there are <Num_bundles> bundles created by <creator_role> with status <status>, Preview Teams <preview_teams>, Release Calendar <add_rel_cal>, Pages <add_stat_page>
        When the <role> logs in
        Then the <role> can approve a bundle

        Examples: bundles
           | role               | Num_bundles | creator_role       | status         | preview_teams |add_rel_cal | add_stat_page |
           | Publishing Admin   | 1           | Publishing Admin   | In_Review      | True          | True       | True          |
           | Publishing Admin   | 1           | Publishing Officer | In_Review      | True          | True       | True          |
           | Publishing Officer | 1           | Publishing Admin   | In_Review      | True          | True       | True          |
           | Publishing Officer | 1           | Publishing Officer | In_Review      | True          | True       | True          |

      Scenario Outline: A user cannot approve known bundle
        Given there is a <role> user
        And there are 1 Statistical Analysis pages
        And there are 1 release calendar pages
        And there are 1 Preview teams
        And the <role> is a member of the Preview teams
        And there are <Num_bundles> bundles created by <creator_role> with status <status>, Preview Teams <preview_teams>, Release Calendar <add_rel_cal>, Pages <add_stat_page>
        When the <role> logs in
        Then the <role> cannot approve a bundle

        Examples: bundles
           | role               | Num_bundles | creator_role       | status         | preview_teams |add_rel_cal | add_stat_page |
           | Viewer             | 1           | Publishing Admin   | In_Review      | True          | True       | True          |


