Feature: CMS users can only delete pages according to our rules

    Background:
        Given a Publishing Admin logs into the admin site

    Scenario: A publishing admin cannot delete a page that has been published
        Given there is a page that has been published
        When the user goes to edit the page
        And the user attempts to delete the page
        Then a banner is displayed indicating that the page cannot be deleted because it has been published previously

    Scenario: A publishing admin can delete a page that has never been published
        Given there is a page that has never been published
        When the user goes to edit the page
        And the user attempts to delete the page
        Then the page is deleted successfully

    Scenario: A publishing admin cannot bulk delete pages that have been published
        Given there are multiple pages, some of which have been published
        When the user goes to the parent page's explorer view
        And the user selects all pages for bulk deletion
        And the user attempts to bulk delete the selected pages
        Then a banner is displayed indicating that the selected pages cannot be deleted because they have been published previously

    Scenario: A publishing admin can bulk delete pages that have not been published
        Given there are multiple pages that have never been published
        When the user goes to the parent page's explorer view
        And the user selects all pages for bulk deletion
        And the user attempts to bulk delete the selected pages
        Then the pages are deleted successfully
