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

    Scenario: A CMS user inputs pm datetime and will see am
        When the user creates and populates a release calendar page
        And the user adds an AM datetime
        And the user clicks "Publish"
        And the user clicks "View Live" on the publish confirmation banner
        Then the datetime is displayed with "am"
    
    Scenario: A CMS user inputs pm datetime and will see pm
        When the user creates and populates a release calendar page
        And the user adds an PM datetime
        And the user clicks "Publish"
        And the user clicks "View Live" on the publish confirmation banner
        Then the datetime is displayed with "pm"