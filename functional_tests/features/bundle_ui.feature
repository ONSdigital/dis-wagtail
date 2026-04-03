Feature: UI Bundle Happy Paths

#---- Bundles Page Search UI Tests -----

Scenario Outline: A user can see the bundles page search
    Given there is a <role> user
    And the <role> logs in
    When the logged in user goes to the bundle page
    Then the logged in user can see the search_term
    And the <role> can see no_bundles
    Examples:
        | role               |
        | Publishing Admin   |
        | Publishing Officer |
        | Viewer             |

Scenario Outline: A user can populate the bundles page search
    Given there is a <role> user
    And the <role> logs in
    And the logged in user goes to the bundle page
    When the logged in user searches for the bundle name not known
    Then the logged in user can see no bundles response
    Examples:
        | role               |
        | Publishing Admin   |
        | Publishing Officer |
        | Viewer             |


Scenario Outline: A user can populate the bundles page search (no existing bundles)
    Given there is a <role> user
    And the <role> logs in
    And the logged in user goes to the bundle page
    When the logged in user searches for the bundle name not known
    Then the logged in user can see no bundles response
    Examples:
        | role               |
        | Publishing Admin   |
        | Publishing Officer |
        | Viewer             |

Scenario Outline: A user can populate the bundles page search
    Given there is a <role> user
    And there is a <creator_role> user
    And there are <number_of_bundles> bundles with <bundle_details>
    And the <role> logs in
    And the logged in user goes to the bundle page
    When the logged in user searches for the bundle name not known
    Then the logged in user can see no bundles response

    Examples: bundles
       | number_of_bundles | role                | creator_role        |  bundle_details                                                                                                                                                |
       | 21                 | Publishing Admin   | Publishing Officer  | {"role": "Publishing Admin",   "creator_role": "Publishing Officer", "status": "Draft", "preview_teams": false, "add_rel_cal": false, "add_stat_page": false} |
       | 21                 | Publishing Officer | Publishing Admin    | {"role": "Publishing Officer", "creator_role": "Publishing Officer", "status": "Draft", "preview_teams": false, "add_rel_cal": false, "add_stat_page": false} |
       | 21                 | Viewer             | Publishing Officer  | {"role": "Publishing Admin",   "creator_role": "Publishing Officer", "status": "Draft", "preview_teams": false, "add_rel_cal": false, "add_stat_page": false} |


Scenario Outline: A User cannot find expected bundle from the bundles page search
    Given there is a <role> user
    And there is a <creator_role> user
    And there is a preview team
    And the <role> is a member of the preview team
    And there are <number_of_bundles> bundles with <bundle_details>
    And the <role> logs in
    And the logged in user goes to the bundle page
    When the logged in user searches for the bundle name not known
    Then the logged in user can see no bundles response


    Examples: bundles
       | number_of_bundles | role                       | creator_role        |  bundle_details                                                                                                                                                |
       | 0                 | Publishing Admin           | Publishing Officer  | {"role": "Publishing Officer", "creator_role": "Publishing Admin",   "status": "Draft", "preview_teams": false, "add_rel_cal": false, "add_stat_page": false} |
       | 0                 | Publishing Officer         | Publishing Admin    | {"role": "Publishing Officer", "creator_role": "Publishing Officer", "status": "Draft", "preview_teams": false, "add_rel_cal": false, "add_stat_page": false} |
       | 0                 | Viewer                     | Publishing Officer  | {"role": "Publishing Officer", "creator_role": "Publishing Officer", "status": "In_Review", "preview_teams": true, "add_rel_cal": false, "add_stat_page": false} |


Scenario Outline: A User can find expected bundle from the bundles page search
    Given there is a <role> user
    And there is a <creator_role> user
    And there is a preview team
    And the <role> is a member of the preview team
    And there are <number_of_bundles> bundles with <bundle_details>
    And the <role> logs in
    And the logged in user goes to the bundle page
    When the logged in user searches for the bundle name known
    Then the logged in user gets match response in bundles search for user <role>

   Examples: bundles
       | number_of_bundles | role                       | creator_role        |  bundle_details                                                                                                                                                |
       | 10                | Publishing Admin           | Publishing Officer  | {"role": "Publishing Admin",   "creator_role": "Publishing Admin",   "status": "Draft", "preview_teams": false, "add_rel_cal": false, "add_stat_page": false} |
       | 10                | Publishing Officer         | Publishing Admin    | {"role": "Publishing Officer", "creator_role": "Publishing Officer", "status": "Draft", "preview_teams": false, "add_rel_cal": false, "add_stat_page": false} |
       | 10                | Viewer                     | Publishing Officer  | {"role": "Viewer",             "creator_role": "Publishing Officer",  "status": "In_Review", "preview_teams": true, "add_rel_cal": false, "add_stat_page": false} |

#---- Bundles Page Create UI Tests -----

Scenario Outline: A User cannot see create button
    Given there is a <role> user
    And the <role> logs in
    When the logged in user goes to the bundle page
    Then the logged in user cannot see the create button

    Examples: bundles
       | role     |
       | Viewer   |

Scenario Outline: A User can see create button
    Given there is a <role> user
    And the <role> logs in
    When the logged in user goes to the bundle page
    Then the logged in user can see the create button

    Examples: bundles
        | role               |
        | Publishing Admin   |
        | Publishing Officer |


Scenario Outline: A User cannot save as draft a bundle that already exists (duplicate name)
    Given there is a <role> user
    And the <role> logs in
    And the logged in user goes to the bundle page
    When the logged in user creates a bundle
    And the user clicks "Save as draft"
    Then the logged in user gets a failure message due to field validation

    Examples: bundles
       | role               |
       | Publishing Admin   |
       | Publishing Officer |

Scenario Outline: A User is unsuccessful to save a save bundle with existing name
    Given there is a <role> user
    And there is a <creator_role> user
    And there are <number_of_bundles> bundles with <bundle_details>
    And the <role> logs in
    And the logged in user goes to the bundle page
    And the logged in user creates a bundle
    And the logged in user adds a Name to the bundle
    When the user clicks "Save as draft"
    Then the logged in user gets a failure message due to duplicate name

    Examples: bundles
       | number_of_bundles | role               | creator_role        |  bundle_details                                                                                                                                                |
       | 1                 | Publishing Admin   | Publishing Officer  | {"role": "Publishing Admin",   "creator_role": "Publishing Officer", "status": "Draft", "preview_teams": false, "add_rel_cal": false, "add_stat_page": false} |
       | 1                 | Publishing Officer | Publishing Admin    | {"role": "Publishing Officer", "creator_role": "Publishing Officer", "status": "Draft", "preview_teams": false, "add_rel_cal": false, "add_stat_page": false} |


Scenario Outline: A User successfully creates and saves a bundle as draft
    Given there is a <role> user
    And the <role> logs in
    And the logged in user goes to the bundle page
    When the logged in user creates a bundle
    And the logged in user adds a Name to the bundle
    And the user clicks "Save as draft"
    Then the logged in user gets a successful create message

    Examples: bundles
       | role               |
       | Publishing Admin   |
       | Publishing Officer |


Scenario Outline: A User cannot save a bundle due to duplicate schedule
    Given there is a <role> user
    And there is a <creator_role> user
    And there is a release calendar page approved by <creator_role>
    And the <role> logs in
    And the logged in user goes to the bundle page
    And the logged in user creates a bundle
    And the logged in user adds a Name to the bundle
    And the logged in user searches for an existing release calendar page
    And the logged in user adds a Release Calendar page to the bundle
    And the logged in user adds a schedule date to the bundle
    When the user clicks "Save as draft"
    Then the logged in user gets a failure message due to duplicate schedule

    Examples: bundles
       | role               | creator_role      |
       | Publishing Officer |Publishing Admin   |
       | Publishing Admin   |Publishing Officer |

Scenario Outline: A User can add a publication date to a bundle
    Given there is a <role> user
    And there is a <creator_role> user
    And the <role> logs in
    And the logged in user goes to the bundle page
    And the logged in user creates a bundle
    And the logged in user adds a Name to the bundle
    When the logged in user adds a schedule date to the bundle
    Then the user clicks "Save as draft"
    And  the logged in user gets a successful create message

    Examples: bundles
       | role               | creator_role      |
       | Publishing Officer |Publishing Admin   |
       | Publishing Admin   |Publishing Officer |

Scenario Outline: A User can find release schedule page
    Given there is a <role> user
    And there is a <creator_role> user
    And there is a release calendar page approved by <creator_role>
    And the <role> logs in
    And the logged in user goes to the bundle page
    And the logged in user creates a bundle
    And the logged in user adds a Name to the bundle
    When the logged in user searches for an existing release calendar page
    Then the logged in user gets match for release calendar search
    When the logged in user adds a Release Calendar page to the bundle
    Then the logged in user confirm the release calendar has been added to the bundle
    When the user clicks "Save as draft"
    Then  the logged in user gets a successful create message

    Examples: bundles
       | role               | creator_role      |
       | Publishing Officer |Publishing Admin   |
       | Publishing Admin   |Publishing Officer |


Scenario Outline: A User cannot find release schedule page
    Given there is a <role> user
    And there is a <creator_role> user
    And there is a release calendar page approved by <creator_role>
    And the <role> logs in
    And the logged in user goes to the bundle page
    And the logged in user creates a bundle
    And the logged in user adds a Name to the bundle
    When the logged in user searches for a non existing release calendar page
    Then the logged in user gets no match for release calendar search

    Examples: bundles
       | role               | creator_role      |
       | Publishing Officer |Publishing Admin   |
       | Publishing Admin   |Publishing Officer |

Scenario Outline: A User cannot find expected bundled_page
    Given there is a <role> user
    And there is a <creator_role> user
    And there is a statistical analysis page approved by <creator_role>
    And the <role> logs in
    And the logged in user goes to the bundle page
    And the logged in user creates a bundle
    And the logged in user adds a Name to the bundle
    When the logged in user searches for a non existing bundled_page
    Then the logged in user gets no match for bundled_page search

    Examples: bundles
       | role               | creator_role      |
       | Publishing Officer |Publishing Admin   |
       | Publishing Admin   |Publishing Officer |

Scenario Outline: A User can find expected bundled_page
    Given there is a <role> user
    And there is a <creator_role> user
    And there is a statistical analysis page approved by <creator_role>
    And there are <number_of_bundles> bundles with <bundle_details>
    And the <role> logs in
    And the logged in user goes to the bundle page
    And the logged in user searches for the bundle name known
    And the logged in user goes to edit bundle
    When the logged in user searches for an existing bundled_page
    And the logged in user gets match for bundled_page search
    And the logged in user adds a bundled page to the bundle
    Then the logged in user confirm the bundled page has been added to the bundle

Examples: bundles
       | number_of_bundles | role                       | creator_role        |  bundle_details                                                                                                                                                |
       | 1                 | Publishing Admin           | Publishing Officer  | {"role": "Publishing Admin",   "creator_role": "Publishing Admin",   "status": "Draft", "preview_teams": false, "add_rel_cal": false, "add_stat_page": false} |
       | 1                 | Publishing Officer         | Publishing Admin    | {"role": "Publishing Officer", "creator_role": "Publishing Officer", "status": "Draft", "preview_teams": false, "add_rel_cal": false, "add_stat_page": false} |


#---- Bundle UI Edit-----
Scenario Outline: A User sucessfully saves and previews a bundle with all features
    Given there is a <role> user
    And there is a <creator_role> user
    And there is a statistical analysis page approved by <creator_role>
    And there is a release calendar page approved by <creator_role>
    And there is a preview team
    And the <role> is a member of the preview team
    And there are <number_of_bundles> bundles with <bundle_details>
    And the <role> logs in
    And the logged in user goes to the bundle page
    And the logged in user searches for the bundle name known
    And the logged in user goes to edit bundle
    And the logged in user searches for an existing release calendar page
    And the logged in user adds a Release Calendar page to the bundle
    And the logged in user searches for an existing bundled_page
    And the logged in user gets match for bundled_page search
    And the logged in user adds a bundled page to the bundle
    And the logged in user can add preview team
    When the user clicks "Save as draft"
    Then the logged in user gets a successful update message
    When the logged in user sends the bundle to preview
    Then the logged in user gets a successful update message

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
    And the logged in user searches for the bundle name known
    When the <role> can preview bundle

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
    And the logged in user searches for the bundle name known
    When the logged in user approves bundle
    Then the logged in user see ready for publish

    Examples: bundles
       | number_of_bundles | role                       | creator_role        |  bundle_details                                                                                                                                                |
       | 1                 | Publishing Admin           | Publishing Admin    | {"role": "Publishing Admin",   "creator_role": "Publishing Admin",   "status": "In_Review", "preview_teams": true, "add_rel_cal": true, "add_stat_page": true} |
       | 1                 | Publishing Admin           | Publishing Officer  | {"role": "Publishing Admin",   "creator_role": "Publishing Officer", "status": "In_Review", "preview_teams": true, "add_rel_cal": true, "add_stat_page": true} |
       | 1                 | Publishing Officer         | Publishing Admin    | {"role": "Publishing Officer", "creator_role": "Publishing Officer", "status": "In_Review", "preview_teams": true, "add_rel_cal": true, "add_stat_page": true} |
       | 1                 | Publishing Officer         | Publishing Officer  | {"role": "Publishing Officer", "creator_role": "Publishing Officer", "status": "In_Review", "preview_teams": true, "add_rel_cal": true, "add_stat_page": true} |


#---- Bundle Cannot Approve UI Tests  -----
Scenario Outline: A user cannot approve a bundle due no bundled pages in bundle
    Given there is a <role> user
    And there is a <creator_role> user
    And there is a preview team
    And the <role> is a member of the preview team
    And there are <number_of_bundles> bundles with <bundle_details>
    And the <role> logs in
    And the logged in user goes to the bundle page
    And the logged in user searches for the bundle name known
    When the logged in user approves bundle
    Then the logged in user does not see Cannot approve the bundle without any pages error

    Examples: bundles
        | number_of_bundles | role                       | creator_role        | bundle_details                                                                                                                                                 |
        | 1                 | Publishing Officer         | Publishing Admin    | {"role": "Publishing Officer", "creator_role": "Publishing Admin", "status": "In_Review", "preview_teams": true, "add_rel_cal": false, "add_stat_page": false} |
        | 1                 | Publishing Admin           | Publishing Officer    | {"role": "Publishing Admin",   "creator_role": "Publishing Officer",   "status": "In_Review", "preview_teams": true, "add_rel_cal": false, "add_stat_page": false} |

