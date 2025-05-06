Feature: CMS users can draft, edit, and publish release pages

    Background:
        Given a contact details snippet exists
        And a superuser logs into the admin site
        And the user navigates to the release calendar page

    Scenario: A CMS user can author and publish release page
        When the user clicks "Add child page" to create a new draft release page
        And the user sets the page status to "Published"
        And the user enters some example content on the page
        And looks up and selects a dataset
        And manually enters a dataset link
        And the user clicks "Publish"
        And the user clicks "View Live" on the publish confirmation banner
        Then the new published release page with the example content is displayed
        And the selected datasets are displayed on the page
        And the user can see the breadcrumbs

    Scenario: Release date text field is visible for provisional releases 
        When the user clicks "Add child page" to create a new draft release page
        Then the page status is set to "Provisional" and the release date text field is visible

    Scenario Outline: Release date text field is hidden for provisional releases 
        When the user clicks "Add child page" to create a new draft release page
        And the user sets the page status to "<PageStatus>"
        Then the date text field is not visible

        Examples:
            | PageStatus   |
            | Confirmed    |
            | Published    |
            | Cancelled    |

    Scenario Outline: A CMS user inputs a datetime on a release calendar page and the correct period is displayed
        When the user clicks "Add child page" to create a new draft release page
        And the user enters some example content on the page
        And the user inputs a <MeridiemIndicator> datetime
        And the user clicks "Publish"
        And the user clicks "View Live" on the publish confirmation banner
        Then the datetime is displayed with "<MeridiemIndicator>"

        Examples:
            | MeridiemIndicator |
            | am                |
            | pm                |
