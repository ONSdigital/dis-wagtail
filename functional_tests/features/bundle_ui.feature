Feature: UI Bundle Happy Paths
    """
    User Role Bundle Life Cycle Happy Path 1 bundle
                                 | Bundles Search | Dashboard Search | Create | Edit | Preview | Approve |
        Publishing Admin         | Can            | ToDo             | Can    | Can  | Can     | Can     !
            As Creator of Bundle | Can            | N/A    | N/A  | N/A     | Cannot  |
            Not Creator          | N/A            | N/A    | N/A  | N/A     | Can     |
        Publishing Officer       | Can            | Can    | Can  | Can     | N/A     |
            As Creator of Bundle | N/A            | N/A    | N/A  | N/A     | Cannot  |
            Not Creator          | N/A            | N/A    | N/A  | N/A     | Can     |
        Viewer                   | N/A            | Cannot | N/A  | N/A     | N/A     |
            not in preview team  | Cannot         | N/A    | N/A  | Cannot  | N/A     |
            in preview team      | Can            | N/A    | N/A  | Can     | N/A     |

    """
#---- Bundle Create UI Tests -----
    Scenario Outline: A User can create a bundle
        Given there is a <role> user
        When the <role> logs in
        Then the user can create a bundle
        And the user can see the created bundle

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
        Given there is a <Role> user
        And there is a <Creator Role> user
        And there are 1 Statistical Analysis pages
        And there are 1 release calendar pages
        And there is a preview team
        And the <Role> is a member of the preview team
        And there are <number_of_bundles> bundles with <Bundle_Details>
        When the <Role> logs in
        Then the user can edit the bundle

        Examples: bundles
           | number_of_bundles | Role                       | Creator Role        | Bundle_Details                                                                                                                                                |
           | 1                 | Publishing Admin           | Publishing Admin    | {"Role": "Publishing Admin",   "Creator Role": "Publishing Admin",   "status": "Draft", "preview_teams": false, "add_rel_cal": false, "add_stat_page": false} |
           | 2                 | Publishing Admin           | Publishing Admin    | {"Role": "Publishing Admin",   "Creator Role": "Publishing Admin",   "status": "Draft", "preview_teams": false, "add_rel_cal": false, "add_stat_page": false} |
           | 11                | Publishing Admin           | Publishing Admin    | {"Role": "Publishing Admin",   "Creator Role": "Publishing Admin",   "status": "Draft", "preview_teams": false, "add_rel_cal": false, "add_stat_page": false} |
           | 1                 | Publishing Admin           | Publishing Officer  | {"Role": "Publishing Admin",   "Creator Role": "Publishing Officer", "status": "Draft", "preview_teams": false, "add_rel_cal": false, "add_stat_page": false} |
           | 1                 | Publishing Officer         | Publishing Admin    | {"Role": "Publishing Officer", "Creator Role": "Publishing Admin",   "status": "Draft", "preview_teams": false, "add_rel_cal": false, "add_stat_page": false} |
           | 1                 | Publishing Officer         | Publishing Officer  | {"Role": "Publishing Officer", "Creator Role": "Publishing Officer", "status": "Draft", "preview_teams": false, "add_rel_cal": false, "add_stat_page": false} |


#---- Bundle Preview UI Tests -----

  Scenario Outline: A User can preview a bundle
        Given there is a <Role> user
        And there is a <Creator Role> user
        And there are 1 Statistical Analysis pages
        And there are 1 release calendar pages
        And there is a preview team
        And the <Role> is a member of the preview team
        And there are <number_of_bundles> bundles with <Bundle_Details>
        When the <Role> logs in
        Then the <Role> can preview a bundle

      Examples: bundles
           | number_of_bundles | Role                       | Creator Role        | Bundle_Details                                                                                                                                              |
           | 1                 | Publishing Admin           | Publishing Admin    | {"Role": "Publishing Admin",   "Creator Role": "Publishing Admin",   "status": "In_Review", "preview_teams": true,  "add_rel_cal": true, "add_stat_page": true} |
           | 1                 | Publishing Officer         | Publishing Admin    | {"Role": "Publishing Officer", "Creator Role": "Publishing Admin",   "status": "In_Review", "preview_teams": true,  "add_rel_cal": true, "add_stat_page": true} |
           | 2                 | Publishing Officer         | Publishing Admin    | {"Role": "Publishing Officer", "Creator Role": "Publishing Admin",   "status": "In_Review", "preview_teams": true,  "add_rel_cal": true, "add_stat_page": true} |
           | 11                | Publishing Officer         | Publishing Admin    | {"Role": "Publishing Officer", "Creator Role": "Publishing Admin",   "status": "In_Review", "preview_teams": true,  "add_rel_cal": true, "add_stat_page": true} |
           | 1                 | Viewer                     | Publishing Admin    | {"Role": "Publishing Admin",   "Creator Role": "Publishing Admin",   "status": "In_Review", "preview_teams": true,  "add_rel_cal": true, "add_stat_page": true} |
           | 2                 | Viewer                     | Publishing Admin    | {"Role": "Publishing Admin",   "Creator Role": "Publishing Admin",   "status": "In_Review", "preview_teams": true,  "add_rel_cal": true, "add_stat_page": true} |
           | 11                | Viewer                     | Publishing Admin    | {"Role": "Publishing Admin",   "Creator Role": "Publishing Admin",   "status": "In_Review", "preview_teams": true,  "add_rel_cal": true, "add_stat_page": true} |
           | 1                 | Publishing Admin           | Publishing Officer  | {"Role": "Publishing Admin",   "Creator Role": "Publishing Officer", "status": "In_Review", "preview_teams": true,  "add_rel_cal": true, "add_stat_page": true} |
           | 1                 | Publishing Officer         | Publishing Officer  | {"Role": "Publishing Officer", "Creator Role": "Publishing Officer", "status": "In_Review", "preview_teams": true,  "add_rel_cal": true, "add_stat_page": true} |
           | 1                 | Viewer                     | Publishing Officer  | {"Role": "Viewer",             "Creator Role": "Publishing Officer", "status": "In_Review", "preview_teams": true,  "add_rel_cal": true, "add_stat_page": true} |


      Scenario Outline: A User cannot preview a bundle
          Given there is a <Role> user
          And there is a <Creator Role> user
          And there are 1 Statistical Analysis pages
          And there are 1 release calendar pages
          And there is a preview team
          And there are <number_of_bundles> bundles with <Bundle_Details>
          When the <Role> logs in
          Then the user cannot preview a bundle

         Examples: bundles
             | number_of_bundles | Role                       | Creator Role        | Bundle_Details                                                                                                                                       |
             | 1                 | Viewer                     | Publishing Admin    | {"Role": "Viewer",             "Creator Role": "Publishing Admin", "status": "In_Review", "preview_teams": false,  "add_rel_cal": true, "add_stat_page": true}|
             | 1                 | Publishing Officer         | Publishing Officer    | {"Role": "Publishing Officer", "Creator Role": "Publishing Officer", "status": "In_Review", "preview_teams": false,  "add_rel_cal": true, "add_stat_page": true} |

#----- Bundle Approve UI Tests -----

      Scenario Outline: A user can approve a bundle
        Given there is a <Role> user
        And there is a <Creator Role> user
        And there are 1 Statistical Analysis pages
        And there are 1 release calendar pages
        And there is a preview team
        And the <Role> is a member of the preview team
        And there are <number_of_bundles> bundles with <Bundle_Details>
        When the <Role> logs in
        Then the user can approve a bundle

        Examples: bundles
            | number_of_bundles | Role                       | Creator Role        | Bundle_Details                                                                                                                                                 |
            | 1                 | Publishing Admin           | Publishing Officer  | {"Role": "Publishing Admin",   "Creator Role": "Publishing Officer", "status": "In_Review", "preview_teams": true, "add_rel_cal": true, "add_stat_page": true} |
            | 1                 | Publishing Officer         | Publishing Admin    | {"Role": "Publishing Officer", "Creator Role": "Publishing Admin",   "status": "In_Review", "preview_teams": true, "add_rel_cal": true, "add_stat_page": true} |


      Scenario Outline: A user cannot approve a bundle
        Given there is a <Role> user
        And there is a <Creator Role> user
        And there are 1 Statistical Analysis pages
        And there are 1 release calendar pages
        And there is a preview team
        And the <Role> is a member of the preview team
        And there are <number_of_bundles> bundles with <Bundle_Details>
        When the <Role> logs in
        Then the user cannot approve a bundle

        Examples: bundles
            | number_of_bundles | Role                       | Creator Role        | Bundle_Details                                                                                                                                                 |
            | 1                 | Viewer                     | Publishing Admin    | {"Role": "Viewer",             "Creator Role": "Publishing Admin",  "status": "In_Review", "preview_teams": false,  "add_rel_cal": true, "add_stat_page": true}|
            | 1                 | Publishing Officer         | Publishing Officer  | {"Role": "Publishing Officer", "Creator Role": "Publishing Officer", "status": "In_Review", "preview_teams": true, "add_rel_cal": true, "add_stat_page": true} |
            | 1                 | Publishing Admin           | Publishing Admin    | {"Role": "Publishing Admin",   "Creator Role": "Publishing Admin",   "status": "In_Review", "preview_teams": true, "add_rel_cal": true, "add_stat_page": true} |

