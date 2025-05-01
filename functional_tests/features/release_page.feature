Feature: CMS users can draft, edit, and publish release pages

    Background:
        Given a contact details snippet exists
        And a superuser logs into the admin site

    Scenario: A CMS user can author and publish release page
        When the user navigates to the release calendar page
        And clicks "add child page" to create a new draft release page
        And the user sets the page status to "Published"
        And enters some example content on the page
        And looks up and selects a dataset
        And manually enters a dataset link
        And the user clicks "Publish"
        And the user clicks "View Live" on the publish confirmation banner
        Then the new published release page with the example content is displayed
        And the selected datasets are displayed on the page
        And the user can see the breadcrumbs

    Scenario Outline: A CMS user inputs a datetime on a release calendar page and the correct period is displayed
        When the user creates and populates a release calendar page
        And the user inputs a <MeridiemIndicator> datetime
        And the user clicks "Publish"
        And the user clicks "View Live" on the publish confirmation banner
        Then the datetime is displayed with "<MeridiemIndicator>"

        Examples:
            | MeridiemIndicator |
            | am                |
            | pm                |
    
    Scenario: A CMS user can see datetime placeholders for the release page
        When the user navigates to the release calendar page
        And clicks "add child page" to create a new draft release page
        Then the datetime placeholder is displayed in the date field for the release page