Feature: UI Bundle Happy Paths
    """

                                 | Bundles Search | Create | Edit | Preview | Approve |
        Publishing Admin         | Can            | Can    | Can  | Can     | Can     !
        Publishing Officer       | Can            | Can    | Can  | Can     | Can     |
        Viewer                   | Can            | Cannot | N/A  | N/A     | N/A     |
            not in preview team  | Can            | N/A    | N/A  | Cannot  | N/A     |
            in preview team      | Can            | N/A    | N/A  | Can     | N/A     |
    """

#---- Bundle Create UI Tests -----
Scenario Outline: A User can create a bundle
    Given there is a <role> user
    And the <role> logs in
    And the logged in user goes to the bundle page
    And the logged in user can see the create button
    When the logged in user can create a bundle
    And the logged in user adds a Name to the bundle
    And the user clicks "Save as draft"
    Then the logged in user gets a success message

    Examples: bundles
       | role               |
       | Publishing Admin   |
       | Publishing Officer |

#---- Bundle Cannot Create UI Tests -----
Scenario Outline: A User cannot create a bundle due to authorisation
    Given there is a <role> user
    And the <role> logs in
    When the logged in user goes to the bundle page
    Then the logged in user cannot see the create button
    Examples: bundles
       | role     |
       | Viewer   |

Scenario Outline: A User cannot create a bundle due to field validation
    Given there is a <role> user
    And the <role> logs in
    And the logged in user goes to the bundle page
    And the logged in user can see the create button
    When the logged in user can create a bundle
    And the user clicks "Save as draft"
    Then the logged in user gets a failure message due to field validation

    Examples: bundles
       | role               |
       | Publishing Admin   |
       | Publishing Officer |


Scenario Outline: A User cannot create a bundle due to already existing
    Given there is a <role> user
    And there is a <creator_role> user
    And there are <number_of_bundles> bundles with <bundle_details>
    And the <role> logs in
    And the logged in user goes to the bundle page
    And the logged in user can see the create button
    And the logged in user can create a bundle
    And the logged in user adds a Name to the bundle
    When the user clicks "Save as draft"
    Then the logged in user gets a failure message due duplicate name

    Examples: bundles
       | number_of_bundles | role               | creator_role        |  bundle_details                                                                                                                                                |
       | 1                 | Publishing Admin   | Publishing Officer  | {"role": "Publishing Admin",   "creator_role": "Publishing Officer", "status": "Draft", "preview_teams": false, "add_rel_cal": false, "add_stat_page": false} |
       | 1                 | Publishing Officer | Publishing Admin    | {"role": "Publishing Officer", "creator_role": "Publishing Officer", "status": "Draft", "preview_teams": false, "add_rel_cal": false, "add_stat_page": false} |

Scenario Outline: A User cannot save a bundle due to duplicate schedule
    Given there is a <role> user
    And there is a <creator_role> user
    And there is a release calendar page approved by <creator_role>
    And the <role> logs in
    And the logged in user goes to the bundle page
    And the logged in user can see the create button
    And the logged in user can create a bundle
    And the logged in user adds a Name to the bundle
    And the logged in user adds a Release Calendar page to the bundle
    And the logged in user add a schedule date to the bundle
    When the user clicks "Save as draft"
    Then the logged in user fails to create a bundle due duplicate schedule

    Examples: bundles
       | role               | creator_role      |
       | Publishing Officer |Publishing Admin   |
       | Publishing Admin   |Publishing Officer |


#---- Bundle UI Edit-----
Scenario Outline: A User can edit a bundle
    Given there is a <role> user
    And there is a <creator_role> user
    And there is a statistical analysis page approved by <creator_role>
    And there is a release calendar page approved by <creator_role>
    And there is a preview team
    And the <role> is a member of the preview team
    And there are <number_of_bundles> bundles with <bundle_details>
    And the <role> logs in
    And the logged in user goes to the bundle page
    And the <role> can find the bundle
    When the logged in user goes to edit bundle
    And the logged in user can add a release schedule
    And the logged in user can add pages
    And the logged in user can add preview team
    Then the user clicks "Save as draft"
    And the logged in user sends the bundle to preview
    And the logged in user gets a bundle update message

    Examples: bundles
       | number_of_bundles | role                       | creator_role        |  bundle_details                                                                                                                                                |
       | 11                | Publishing Admin           | Publishing Admin    | {"role": "Publishing Admin",   "creator_role": "Publishing Admin",   "status": "Draft", "preview_teams": false, "add_rel_cal": false, "add_stat_page": false} |
       | 1                 | Publishing Admin           | Publishing Officer  | {"role": "Publishing Admin",   "creator_role": "Publishing Officer", "status": "Draft", "preview_teams": false, "add_rel_cal": false, "add_stat_page": false} |
       | 1                 | Publishing Officer         | Publishing Admin    | {"role": "Publishing Officer", "creator_role": "Publishing Officer", "status": "Draft", "preview_teams": false, "add_rel_cal": false, "add_stat_page": false} |
       | 2                 | Publishing Officer         | Publishing Officer  | {"role": "Publishing Officer", "creator_role": "Publishing Officer", "status": "Draft", "preview_teams": false, "add_rel_cal": false, "add_stat_page": false} |

#---- Bundle Preview UI Tests  -----

Scenario Outline: A User can preview a bundle
    Given there is a <role> user
    And there is a <creator_role> user
    And there is a statistical analysis page approved by <creator_role>
    And there is a release calendar page approved by <creator_role>
    And there is a preview team
    And the <role> is a member of the preview team
    And there are <number_of_bundles> bundles with <bundle_details>
    And the <role> logs in
    And the logged in user goes to the bundle page
    When the <role> can find the bundle
    Then  the <role> can preview bundle

  Examples: bundles
       | number_of_bundles | role                       | creator_role        | bundle_details                                                                                                                                              |
       | 1                 | Publishing Admin           | Publishing Admin    | {"role": "Publishing Admin",   "creator_role": "Publishing Admin",   "status": "In_Review", "preview_teams": true,  "add_rel_cal": true, "add_stat_page": true} |
       | 2                 | Publishing Officer         | Publishing Admin    | {"role": "Publishing Officer", "creator_role": "Publishing Admin",   "status": "In_Review", "preview_teams": true,  "add_rel_cal": true, "add_stat_page": true} |
       | 11                | Viewer                     | Publishing Admin    | {"role": "Viewer",             "creator_role": "Publishing Admin",   "status": "In_Review", "preview_teams": true,  "add_rel_cal": true, "add_stat_page": true} |
       | 11                | Publishing Admin           | Publishing Officer  | {"role": "Publishing Admin",   "creator_role": "Publishing Officer", "status": "In_Review", "preview_teams": true,  "add_rel_cal": true, "add_stat_page": true} |
       | 1                 | Publishing Officer         | Publishing Officer  | {"role": "Publishing Officer", "creator_role": "Publishing Officer", "status": "In_Review", "preview_teams": true,  "add_rel_cal": true, "add_stat_page": true} |
       | 2                 | Viewer                     | Publishing Officer  | {"role": "Viewer",             "creator_role": "Publishing Officer", "status": "In_Review", "preview_teams": true,  "add_rel_cal": true, "add_stat_page": true} |


#---- Bundle Cannot preview UI Tests -----
Scenario Outline: A User cannot preview a bundle due to not being a member of an associated preview-team
    Given there is a <role> user
    And there is a <creator_role> user
    And there is a statistical analysis page approved by <creator_role>
    And there is a release calendar page approved by <creator_role>
    And there is a preview team
    And there are <number_of_bundles> bundles with <bundle_details>
    And the <role> logs in
    When the logged in user goes to the bundle page
    Then the logged in user cannot find the bundle

 Examples: bundles
     | number_of_bundles | role                       | creator_role        | bundle_details                                                                                                                                       |
     | 1                 | Viewer                     | Publishing Admin    | {"role": "Viewer", "creator_role": "Publishing Admin", "status": "In_Review", "preview_teams": false,  "add_rel_cal": true, "add_stat_page": true}|


#----- Bundle Approve UI Tests -----

Scenario Outline: A user can approve a bundle
    Given there is a <role> user
    And there is a <creator_role> user
    And there is a statistical analysis page approved by <creator_role>
    And there is a release calendar page approved by <creator_role>
    And there is a preview team
    And the <role> is a member of the preview team
    And there are <number_of_bundles> bundles with <bundle_details>
    And the <role> logs in
    And the logged in user goes to the bundle page
    When the <role> can find the bundle
    Then the logged in user can approve a bundle

    Examples: bundles
       | number_of_bundles | role                       | creator_role        |  bundle_details                                                                                                                                                |
       | 1                 | Publishing Admin           | Publishing Admin    | {"role": "Publishing Admin",   "creator_role": "Publishing Admin",   "status": "In_Review", "preview_teams": true, "add_rel_cal": true, "add_stat_page": true} |
       | 1                 | Publishing Admin           | Publishing Officer  | {"role": "Publishing Admin",   "creator_role": "Publishing Officer", "status": "In_Review", "preview_teams": true, "add_rel_cal": true, "add_stat_page": true} |
       | 1                 | Publishing Officer         | Publishing Admin    | {"role": "Publishing Officer", "creator_role": "Publishing Officer", "status": "In_Review", "preview_teams": true, "add_rel_cal": true, "add_stat_page": true} |
       | 1                 | Publishing Officer         | Publishing Officer  | {"role": "Publishing Officer", "creator_role": "Publishing Officer", "status": "In_Review", "preview_teams": true, "add_rel_cal": true, "add_stat_page": true} |


#---- Bundle Cannot Approve UI Tests  -----
Scenario Outline: A user cannot approve a bundle due no bundle pages in bundle
    Given there is a <role> user
    And there is a <creator_role> user
    And there is a preview team
    And the <role> is a member of the preview team
    And there are <number_of_bundles> bundles with <bundle_details>
    And the <role> logs in
    And the logged in user goes to the bundle page
    When the <role> can find the bundle
    Then the logged in user cannot approve a bundle due to lack of pages

    Examples: bundles
        | number_of_bundles | role                       | creator_role        | bundle_details                                                                                                                                                 |
        | 1                 | Publishing Officer         | Publishing Admin    | {"role": "Publishing Officer", "creator_role": "Publishing Admin", "status": "In_Review", "preview_teams": true, "add_rel_cal": false, "add_stat_page": false} |
        | 1                 | Publishing Admin           | Publishing Officer    | {"role": "Publishing Admin",   "creator_role": "Publishing Officer",   "status": "In_Review", "preview_teams": true, "add_rel_cal": false, "add_stat_page": false} |

