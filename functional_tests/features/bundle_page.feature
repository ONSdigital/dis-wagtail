Feature: Publishing Officer can draft, edit, and publish bundles


    Scenario: A Publishing Officer can add Bundles with Publishing Officer as the creator.  The bundle can be seen and accessed.
    Once the creator is removed from the bundle then the bundle can still be seen and accessed

        Given a Publishing Officer logs into the admin site
        And the user can see the Bundles menu item
        And the user can add Bundles created by user
        And is ready for review
        And has a preview team
        Then the user can see the Bundles menu item with creator
        And the user can inspect Bundle details with creator
#        When Bundle has the creator removed
#        Then the user can see the Bundles menu item without creator
#        And the user can inspect Bundle details without creator


