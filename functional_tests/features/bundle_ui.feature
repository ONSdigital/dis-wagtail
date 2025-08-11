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
        Given there is a <Role> user
        And there is a <Creator Role> user
        And there are 1 Statistical Analysis pages
        And there are 1 release calendar pages
        And there are 1 Preview teams
        And the <Role> is a member of the Preview teams
        And there are <Number_of_Bundles> bundles with <Bundle_Details>
        When the <Role> logs in
        Then the <Role> can edit a bundle

        Examples: bundles
           | Number_of_Bundles | Role                       | Creator Role        | Bundle_Details                                                                                                                                                         |
           | 1                 | "Publishing Admin"         | Publishing Admin    | {"Role":"Publishing Admin","Creator Role":"Publishing Admin","status":"Draft","preview_teams":false,"add_rel_cal":false,"add_stat_page":false} |
           | 1                 | '{"Role": "Publishing Officer", "Creator Role": "Publishing Officer",  "status": "Draft", "preview_teams":"False",  "add_rel_cal": "False",  "add_stat_page": "False"}' |
           | 1                 | '{"Role": "Publishing Admin", "Creator Role": "Publishing Officer",  "status": "Draft", "preview_teams":"False",  "add_rel_cal": "False",  "add_stat_page": "False"}' |
           | 1                 | '{"Role": "Publishing Officer", "Creator Role": "Publishing Admin",  "status": "Draft", "preview_teams":"False",  "add_rel_cal": "False",  "add_stat_page": "False"}' |


#---- Bundle Preview UI Tests -----

  Scenario Outline: A User can preview a bundle
        Given there is a <role> user
        And there is a <Creator Role> user
        And there are 1 Statistical Analysis pages
        And there are 1 release calendar pages
        And there are 1 Preview teams
        And the <role> is a member of the Preview teams
        And there are <Number_of_Bundles> bundles with <Bundle_Details>
        When the <role> logs in
        Then the <role> can preview a bundle

      Examples: bundles
           | Number_of_Bundles | Bundle_Details                                                                                                                                                         |
           | 1                 | '{"Role": "Publishing Admin", "Creator_Role": "Publishing Admin",  "status": "In_Review", "preview_teams":"True"  "add_rel_cal":"True", "add_stat_page": "True"}'       |
           | 1                 | '{"Role": "Publishing Officer", "Creator_Role": "Publishing Admin",  "status": "In_Review", "preview_teams":"True"  "add_rel_cal": "True",  "add_stat_page": "True"}' |
           | 1                 | '{"Role": "Viewer", "Creator_Role": "Publishing Admin",  "status": "In_Review", "preview_teams":"True"  "add_rel_cal": "True",  "add_stat_page": "True"}' |
           | 1                 | '{"Role": "Publishing Admin", "Creator_Role": "Publishing Officer",  "status": "In_Review", "preview_teams":"True"  "add_rel_cal":"True", "add_stat_page": "True"}'       |
           | 1                 | '{"Role": "Publishing Officer", "Creator_Role": "Publishing Officer",  "status": "In_Review", "preview_teams":"True"  "add_rel_cal": "True",  "add_stat_page": "True"}' |
           | 1                 | '{"Role": "Viewer", "Creator_Role": "Publishing Officer",  "status": "In_Review", "preview_teams":"True"  "add_rel_cal": "True",  "add_stat_page": "True"}' |


      Scenario Outline: A User cannot preview a bundle
        Given there is a <role> user
        And there are 1 Statistical Analysis pages
        And there are 1 release calendar pages
        And there are 1 Preview teams
        And there are <Number_of_Bundles> bundles with <Bundle_Details>
        When the <role> logs in
        Then the <role> cannot preview a bundle

         Examples: bundles
           | Number_of_Bundles | Bundle_Details                                                                                                                                                         |
           | 1                 | '{"Role": "Viewer", "Creator_Role": "Publishing Admin",  "status": "In_Review", "preview_teams":"False"  "add_rel_cal":"True", "add_stat_page": "True"}'       |


      Scenario Outline: A user can approve known bundle
        Given there is a <role> user
        And there are 1 Statistical Analysis pages
        And there are 1 release calendar pages
        And there are 1 Preview teams
        And the <role> is a member of the Preview teams
        And there are <Number_of_Bundles> bundles with <Bundle_Details>
        When the <role> logs in
        Then the <role> can approve a bundle

        Examples: bundles
           | Number_of_Bundles | Bundle_Details                                                                                                                                                         |
           | 1                 | '{"Role": "Publishing Admin", "Creator_Role": "Publishing Admin",  "status": "In_Review", "preview_teams":"True",  "add_rel_cal":"True", "add_stat_page": "True"}'       |
           | 1                 | '{"Role": "Publishing Admin", "Creator_Role": "Publishing Officer",  "status": "In_Review", "preview_teams":"True", "add_rel_cal":"True", "add_stat_page": "True"}'       |
           | 1                 | '{"Role": "Publishing Officer", "Creator_Role": "Publishing Admin",  "status": "In_Review", "preview_teams":"True", "add_rel_cal": "True",  "add_stat_page": "True"}' |
           | 1                 | '{"Role": "Publishing Officer", "Creator_Role": "Publishing Officer",  "status": "In_Review", "preview_teams":"True" , "add_rel_cal": "True",  "add_stat_page": "True"}' |


      Scenario Outline: A user cannot approve known bundle
        Given there is a <role> user
        And there are 1 Statistical Analysis pages
        And there are 1 release calendar pages
        And there are 1 Preview teams
        And the <role> is a member of the Preview teams
        And there are <Number_of_Bundles> bundles with <Bundle_Details>
        When the <role> logs in
        Then the <role> cannot approve a bundle

        Examples: bundles
           | Number_of_Bundles | Bundle_Details                                                                                                                                                         |
           | 1                 | '{"Role": "Viewer", "Creator_Role": "Publishing Admin",  "status": "In_Review", "preview_teams":"True"  "add_rel_cal":"True", "add_stat_page": "True"}'       |


