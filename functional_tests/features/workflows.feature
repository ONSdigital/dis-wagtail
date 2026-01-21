Feature: Page-level workflows

    Background:
        Given a statistical article exists

    Scenario: A Publishing team user cannot self-approve a page if making edits
        Given the statistical article page is "in preview"
        When a Publishing Officer logs into the admin site
        And  the user edits the statistical article page
        And  the user updates the statistical article page content
        And  the user clicks the action button toggle
        Then the "Approve" button is disabled
        And  the "Approve with comment" button is disabled


    Scenario: A Publishing team user cannot see the approve buttons if they are the last editor
        Given the statistical article page is "in preview"
        When a Publishing Officer logs into the admin site
        And  the user edits the statistical article page
        And  the user is the last statistical article page editor
        Then the "Approve" button does not exist
        And  the "Approve with comment" button does not exist


    Scenario: A Publishing Admin can unlock a page locked by someone else, when it is in the review workflow step
        Given the statistical article page is "in preview"
        And  the statistical article page is locked by another user
        When a Publishing Admin logs into the admin site
        And  the user edits the statistical article page
        Then the "Unlock" button exists
        And  the user can unlock the page


    Scenario: A Publishing Officer can unlock a page locked by them, when it is in the review workflow step
        Given the statistical article page is "in preview"
        And the statistical article page is locked by a Publishing Officer
        And the user is logged in
        When the user edits the statistical article page
        Then the "Unlock" button exists
        And  the user can unlock the page


    Scenario: A Publishing Officer cannot unlock a page locked by a Publishing Admin, when it is in the review workflow step
        Given the statistical article page is "in preview"
        And  the statistical article page is locked by a Publishing Admin
        When a Publishing Officer logs into the admin site
        And  the user edits the statistical article page
        Then the "Unlock" button doesn't exist


    Scenario Outline: When page is Approved (Ready to publish), it should be locked for editing
        Given the statistical article page is "ready to publish"
        When a <user> logs into the admin site
        And  the user edits the statistical article page
        Then the "This page cannot be edited as it is Ready to be published." text is displayed
        And  the "Page locked" button exists

    Examples:
        | user               |
        | Publishing Officer |
        | Publishing Admin   |


    Scenario: When page is Approved (Ready to publish), then a Publishing admin can "unlock" it
        Given the statistical article page is "ready to publish"
        When a Publishing Admin logs into the admin site
        And  the user edits the statistical article page
        And  the user clicks the action button toggle
        Then the "Unlock editing" link exists
        And  the user can unlock the page for editing
        And  the "Page editing unlocked." text is displayed
        And  the "Unlock editing" link does not exist


    Scenario: When page is Approved (Ready to publish) and in a work in progress bundle, then a Publishing admin can "unlock" it
        Given the statistical article page is "ready to publish"
        When a Publishing Admin logs into the admin site
        And  the statistical article page is in a "In Preview" bundle
        And  the user edits the statistical article page
        And  the user clicks the action button toggle
        Then the "Unlock editing" link exists
        And  the user can unlock the page for editing
        And  the "Page editing unlocked." text is displayed
        And  the "Unlock editing" link does not exist


    Scenario: When page is Approved (Ready to publish) and in an Approved bundle, then a Publishing admin cannot "unlock" it
        Given the statistical article page is "Ready to publish"
        When a Publishing Admin logs into the admin site
        And  the statistical article page is in a "Ready to publish" bundle
        And  the user edits the statistical article page
        Then the "Page locked" button exists
        And  the "Unlock editing" link does not exist
        And  the "This page is included in a bundle that is ready to be published. You must revert the bundle to Draft or In preview in order to make further changes." text is displayed


    Scenario Outline: When page is Approved (Ready to publish) and not in a bundle, a <publishing user> can publish it
        Given the statistical article page is "ready to publish"
        When a <publishing user> logs into the admin site
        And  the user edits the statistical article page
        And  the user clicks the action button toggle
        And  the "Publish" button exists
        And  the user clicks the "Publish" button
        And  the user clicks "View Live" on the publish confirmation banner
        Then the published statistical article page is displayed

    Examples:
        | publishing user    |
        | Publishing Admin   |
        | Publishing Officer |
        | superuser          |


    Scenario Outline: When page is Approved (Ready to publish) and in a bundle, a <publishing user> cannot publish it
        Given the statistical article page is "ready to publish"
        And  the statistical article page is in a "Draft" bundle
        When a <publishing user> logs into the admin site
        And  the user edits the statistical article page
        And  the user clicks the action button toggle
        Then the "Publish" button does not exist

    Examples:
        | publishing user    |
        | Publishing Admin   |
        | Publishing Officer |
        | superuser          |
