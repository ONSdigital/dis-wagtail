Feature: CMS users can create the footer menu
    Scenario: A CMS user can create footer menu instance
        Given a CMS user logs into the admin site
        And the user creates a footer menu
        And the user populates the footer menu
        And the user clicks the "Save Draft" button
        And the user clicks "View Live"
        Then the preview of the footer menu is displayed with the populated data

    Scenario: Validation errors are raised when footer menu is left empty
        Given a CMS user logs into the admin site
        When the user creates a footer menu
        And the user inputs empty footer
        And the user clicks the "Save Draft" button
        Then an error message is presented

    Scenario: A CMS user can edit the footer menu
        Given a CMS user logs into the admin site
        And a pre-populated footer menu exists
        When the user edits a footer menu
        And the user clicks the "Save Draft" button
        And the user clicks "View Live"
        Then the preview of the footer menu is displayed with the edited data

    Scenario: Validation errors are raised when duplicate links are entered on the footer menu
        Given a CMS user logs into the admin site
        And a pre-populated footer menu exist
        When user adds a duplicate link
        And the user clicks the "Save Draft" button
        Then an error message is displayed next to the duplicated link field

    Scenario: a CMS user can assign footer menu in navigation settings
        Given a CMS user logs into the admin site
        And a footer menu exists
        And a CMS user navigates to "Navigation settings"
        When no footer menu is selected
        And chooses footer menu
        And clicks "saves"
        Then footer menu is assigned
