Feature: CMS users can draft, edit, and publish release pages

    Background:
        Given a contact details snippet exists
        And a superuser logs into the admin site
        And the user navigates to the release calendar page

     Scenario: A CMS user can see datetime placeholders for the release page by textbox
        When the user clicks "Add child page" to create a new draft release page
        Then the date placeholder, "YYYY-MM-DD HH:MM", is displayed in the date input textboxes

    Scenario: Release date text field is visible for provisional releases
        When the user clicks "Add child page" to create a new draft release page
        Then the page status is set to "Provisional" and the release date text field is visible

    Scenario: Release date text field is added
        When the user clicks "Add child page" to create a new draft release page
        And the user enters some example content on the page
        And the user adds a release date text
        And the user clicks "Publish"
        And the user clicks "View Live" on the publish confirmation banner
        Then the release date text is displayed

    Scenario Outline: Release date text field is hidden for provisional releases
        When the user clicks "Add child page" to create a new draft release page
        And the user sets the page status to "<PageStatus>"
        Then the date text field is not visible

        Examples:
            | PageStatus   |
            | Confirmed    |
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
