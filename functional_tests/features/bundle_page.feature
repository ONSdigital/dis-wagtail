Feature: Publishing Officer can draft, edit, and publish bundles
# Viewer
# Publishing Admin
# Publishing Officer
    Background:
        Given a Publishing Officer logs into the admin site
        And the user can see the Bundles menu item
        When the user clicks the Bundles menu item
        Then the user can add Bundles

    Scenario: A Viewer can inspect Bundles details
        When a Viewer logs into the admin site
        And the viewer is in the preview team
        Then the user can see the Bundle menu item
        And the user can inspect Bundle details

    Scenario: A Viewer can inspect Bundles details
        Given a Publishing Admin logs into the admin site
        And Bundle has the creator removed
        When a Viewer logs into the admin site
        And the Viewer is in the preview team
        Then the user can see the Bundle menu item
        And the user can inspect Bundle details

