Feature: UI Bundle Happy Paths
    """
    User role Bundle Life Cycle Happy Path 1 bundle Authorisation summary
                                 | Bundles Search | Dashboard Search | Create | Edit | Preview | Approve |
        Publishing Admin         | Can            |                  | Can    | Can  | Can     | Can     !
            As Creator of Bundle | N/A            | N/A              | N/A    | N/A  | N/A     | Cannot  |
            Not Creator          | N/A            | N/A              | N/A    | N/A  | N/A     | Can     |
        Publishing Officer       | Can            | N/A              | Can    | Can  | Can     | N/A     |
            As Creator of Bundle | N/A            | N/A              | N/A    | N/A  | N/A     | Cannot  |
            Not Creator          | N/A            | N/A              | N/A    | N/A  | N/A     | Can     |
        Viewer                   | N/A            | N/A              | Cannot | N/A  | N/A     | N/A     |
            not in preview team  | Cannot         | N/A              | N/A    | N/A  | Cannot  | N/A     |
            in preview team      | Can            | N/A              | N/A    | N/A  | Can     | N/A     |
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

#---- Bundle Edit UI Tests -----
    Scenario Outline: A User can edit a bundle with release calendar single and multi bundles
        Given there is a <role> user
        And there is a <creator_role> user
        And there are 1 Statistical Analysis pages
        And there are 1 release calendar pages
        And there is a preview team
        And the <role> is a member of the preview team
        And there are <number_of_bundles> bundles with <bundle_details>
        When the <role> logs in
        Then the user can edit the bundle

        Examples: bundles
           | number_of_bundles | role                       | creator_role        |  bundle_details                                                                                                                                                |
           | 1                 | Publishing Admin           | Publishing Admin    | {"role": "Publishing Admin",   "creator_role": "Publishing Admin",   "status": "Draft", "preview_teams": false, "add_rel_cal": false, "add_stat_page": false} |
           | 2                 | Publishing Admin           | Publishing Admin    | {"role": "Publishing Admin",   "creator_role": "Publishing Admin",   "status": "Draft", "preview_teams": false, "add_rel_cal": false, "add_stat_page": false} |
           | 11                | Publishing Admin           | Publishing Admin    | {"role": "Publishing Admin",   "creator_role": "Publishing Admin",   "status": "Draft", "preview_teams": false, "add_rel_cal": false, "add_stat_page": false} |
           | 1                 | Publishing Admin           | Publishing Officer  | {"role": "Publishing Admin",   "creator_role": "Publishing Officer", "status": "Draft", "preview_teams": false, "add_rel_cal": false, "add_stat_page": false} |
           | 1                 | Publishing Officer         | Publishing Admin    | {"role": "Publishing Officer", "creator_role": "Publishing Admin",   "status": "Draft", "preview_teams": false, "add_rel_cal": false, "add_stat_page": false} |
           | 1                 | Publishing Officer         | Publishing Officer  | {"role": "Publishing Officer", "creator_role": "Publishing Officer", "status": "Draft", "preview_teams": false, "add_rel_cal": false, "add_stat_page": false} |

    Scenario Outline: A User can edit a bundle with release date single
        Given there is a <role> user
        And there is a <creator_role> user
        And there are 1 Statistical Analysis pages
        And there is a preview team
        And the <role> is a member of the preview team
        And there are <number_of_bundles> bundles with <bundle_details>
        When the <role> logs in
        Then the user can edit the bundle

        Examples: bundles
           | number_of_bundles | role                       | creator_role        | bundle_details                                                                                                                                                |
           | 1                 | Publishing Admin           | Publishing Admin    | {"role": "Publishing Admin",   "creator_role": "Publishing Admin",   "status": "Draft", "preview_teams": false, "add_rel_cal": false, "add_stat_page": false} |
           | 1                 | Publishing Admin           | Publishing Officer  | {"role": "Publishing Admin",   "creator_role": "Publishing Officer", "status": "Draft", "preview_teams": false, "add_rel_cal": false, "add_stat_page": false} |
           | 1                 | Publishing Officer         | Publishing Admin    | {"role": "Publishing Officer", "creator_role": "Publishing Admin",   "status": "Draft", "preview_teams": false, "add_rel_cal": false, "add_stat_page": false} |
           | 1                 | Publishing Officer         | Publishing Officer  | {"role": "Publishing Officer", "creator_role": "Publishing Officer", "status": "Draft", "preview_teams": false, "add_rel_cal": false, "add_stat_page": false} |


#---- Bundle Preview UI Tests -----

  Scenario Outline: A User can preview a bundle
        Given there is a <role> user
        And there is a <creator_role> user
        And there are 1 Statistical Analysis pages
        And there are 1 release calendar pages
        And there is a preview team
        And the <role> is a member of the preview team
        And there are <number_of_bundles> bundles with <bundle_details>
        When the <role> logs in
        Then the <role> can preview a bundle

      Examples: bundles
           | number_of_bundles | role                       | creator_role        | bundle_details                                                                                                                                              |
           | 1                 | Publishing Admin           | Publishing Admin    | {"role": "Publishing Admin",   "creator_role": "Publishing Admin",   "status": "In_Review", "preview_teams": true,  "add_rel_cal": true, "add_stat_page": true} |
           | 1                 | Publishing Officer         | Publishing Admin    | {"role": "Publishing Officer", "creator_role": "Publishing Admin",   "status": "In_Review", "preview_teams": true,  "add_rel_cal": true, "add_stat_page": true} |
           | 2                 | Publishing Officer         | Publishing Admin    | {"role": "Publishing Officer", "creator_role": "Publishing Admin",   "status": "In_Review", "preview_teams": true,  "add_rel_cal": true, "add_stat_page": true} |
           | 11                | Publishing Officer         | Publishing Admin    | {"role": "Publishing Officer", "creator_role": "Publishing Admin",   "status": "In_Review", "preview_teams": true,  "add_rel_cal": true, "add_stat_page": true} |
           | 1                 | Viewer                     | Publishing Admin    | {"role": "Publishing Admin",   "creator_role": "Publishing Admin",   "status": "In_Review", "preview_teams": true,  "add_rel_cal": true, "add_stat_page": true} |
           | 2                 | Viewer                     | Publishing Admin    | {"role": "Publishing Admin",   "creator_role": "Publishing Admin",   "status": "In_Review", "preview_teams": true,  "add_rel_cal": true, "add_stat_page": true} |
           | 11                | Viewer                     | Publishing Admin    | {"role": "Publishing Admin",   "creator_role": "Publishing Admin",   "status": "In_Review", "preview_teams": true,  "add_rel_cal": true, "add_stat_page": true} |
           | 1                 | Publishing Admin           | Publishing Officer  | {"role": "Publishing Admin",   "creator_role": "Publishing Officer", "status": "In_Review", "preview_teams": true,  "add_rel_cal": true, "add_stat_page": true} |
           | 1                 | Publishing Officer         | Publishing Officer  | {"role": "Publishing Officer", "creator_role": "Publishing Officer", "status": "In_Review", "preview_teams": true,  "add_rel_cal": true, "add_stat_page": true} |
           | 1                 | Viewer                     | Publishing Officer  | {"role": "Viewer",             "creator_role": "Publishing Officer", "status": "In_Review", "preview_teams": true,  "add_rel_cal": true, "add_stat_page": true} |

#----- Bundle Approve UI Tests -----

    Scenario Outline: A user can approve a bundle
        Given there is a <role> user
        And there is a <creator_role> user
        And there are 1 Statistical Analysis pages
        And there are 1 release calendar pages
        And there is a preview team
        And the <role> is a member of the preview team
        And there are <number_of_bundles> bundles with <bundle_details>
        When the <role> logs in
        Then the user can approve a bundle

        Examples: bundles
            | number_of_bundles | role                       | creator_role        | bundle_details                                                                                                                                                 |
            | 1                 | Publishing Admin           | Publishing Officer  | {"role": "Publishing Admin",   "creator_role": "Publishing Officer", "status": "In_Review", "preview_teams": true, "add_rel_cal": true, "add_stat_page": true} |
            | 1                 | Publishing Officer         | Publishing Admin    | {"role": "Publishing Officer", "creator_role": "Publishing Admin",   "status": "In_Review", "preview_teams": true, "add_rel_cal": true, "add_stat_page": true} |

#---- Bundle Cannot Create UI Tests -----
    Scenario Outline: A User cannot create a bundle due to authorisation
        Given there is a <role> user
        When the <role> logs in
        Then the user cannot create a bundle
        Examples: bundles
           | role     |
           | Viewer   |

    Scenario Outline: A User cannot create a bundle due field validation
        Given there is a <role> user
        When the <role> logs in
        Then the user fails to create a bundle due to mandatory field

        Examples: bundles
           | role               |
           | Publishing Admin   |
           | Publishing Officer |

    Scenario Outline: A User cannot create a bundle due to duplicate schedule
        Given there is a <role> user
        And there are 1 release calendar pages
        When the <role> logs in
        Then the user fails to create a bundle due to duplicate release dates

        Examples: bundles
           | role               |
           | Publishing Admin   |
           | Publishing Officer |

#---- Bundle Cannot preview UI Tests -----
    Scenario Outline: A User cannot preview a bundle due to authorisation
      Given there is a <role> user
      And there is a <creator_role> user
      And there are 1 Statistical Analysis pages
      And there are 1 release calendar pages
      And there is a preview team
      And there are <number_of_bundles> bundles with <bundle_details>
      When the <role> logs in
      Then the user cannot preview a bundle

     Examples: bundles
         | number_of_bundles | role                       | creator_role        | bundle_details                                                                                                                                       |
         | 1                 | Viewer                     | Publishing Admin    | {"role": "Viewer",             "creator_role": "Publishing Admin", "status": "In_Review", "preview_teams": false,  "add_rel_cal": true, "add_stat_page": true}|
         | 1                 | Publishing Officer         | Publishing Officer  | {"role": "Publishing Officer", "creator_role": "Publishing Officer", "status": "In_Review", "preview_teams": false,  "add_rel_cal": true, "add_stat_page": true} |

#---- Bundle Cannot Approve UI Tests -----
    Scenario Outline: A user cannot approve a bundle due to authorisation
        Given there is a <role> user
        And there is a <creator_role> user
        And there are 1 Statistical Analysis pages
        And there are 1 release calendar pages
        And there is a preview team
        And the <role> is a member of the preview team
        And there are <number_of_bundles> bundles with <bundle_details>
        When the <role> logs in
        Then the user cannot approve a bundle

        Examples: bundles
            | number_of_bundles | role                       | creator_role        | bundle_details                                                                                                                                                 |
            | 1                 | Viewer                     | Publishing Admin    | {"role": "Viewer",             "creator_role": "Publishing Admin",  "status": "In_Review", "preview_teams": false,  "add_rel_cal": true, "add_stat_page": true}|
            | 1                 | Publishing Officer         | Publishing Officer  | {"role": "Publishing Officer", "creator_role": "Publishing Officer", "status": "In_Review", "preview_teams": true, "add_rel_cal": true, "add_stat_page": true} |
            | 1                 | Publishing Admin           | Publishing Admin    | {"role": "Publishing Admin",   "creator_role": "Publishing Admin",   "status": "In_Review", "preview_teams": true, "add_rel_cal": true, "add_stat_page": true} |

