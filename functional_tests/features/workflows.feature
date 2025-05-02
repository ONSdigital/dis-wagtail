Feature: Page-level workflows

    Background:
        Given a Publishing Officer logs into the admin site
        And a statistical article exists
        And the statistical article page is "in preview"

    Scenario: A Publishing team user cannot self-approve a page if making edits
        When the user edits the statistical article page
        And the user updates the statistical article page content
        And the user clicks the action button toggle
        Then the "Approve" button is disabled
        And the "Approve with comment" button is disabled


    Scenario: A Publishing team user cannot see the approve buttons if they are the last editor
        When the user edits the statistical article page
        And the user is the last statistical article page editor
        Then the "Approve" button does not exist
        And the "Approve with comment" button does not exist
