Feature: Publishing Officer can draft, edit, and publish bundles

    Scenario: A Publishing Officer adds a bundle and the added by is populated with the creator
        Given a Publishing Officer logs into the admin site
        When a bundle has been created with name "Test 1" and creator
        Then the user goes to the bundle menu page
        And the bundle menu shows bundle with name "Test 1" and created by is not empty

    Scenario: A Publishing Officer adds a bundle and the inspect page for the bundle shows the created by as populated
        Given a Publishing Officer logs into the admin site
        And a bundle has been created with name "Test 1" and creator
        When the user goes to the bundle inspect page
        Then the user can inspect Bundle details and creator

    Scenario: A Publishing Admin can see the Bundles Menu and that a bundle with creator removed
        Given a Publishing Officer logs into the admin site
        When a bundle has been created with name "Test 1" and creator
        And the bundle has creator removed
        Then the user goes to the bundle menu page
        And the bundle menu shows bundle with name "Test 1" and created by is empty

    Scenario: A Publishing Admin can see the Bundle Inspect and that the bundle with creator removed
        Given a Publishing Officer logs into the admin site
        And a bundle has been created with name "Test 1" and creator
        And the bundle has creator removed
        When the user goes to the bundle inspect page
        Then the user can inspect Bundle details and creator has no entry

