Feature: CMS users can manage the footer menu
    Scenario: A CMS user can create and preview a footer menu
        Given a CMS user logs into the admin site
        When the user creates a footer menu
        And the user populates the footer menu
        And the user clicks "save draft"
        And the user clicks "View Live"
        Then the preview of the footer menu is displayed with the populated data
    
    Scenario: A CMS user can edit the footer menu
        Given a CMS user logs into the admin site
        And pre-populated footer menu exists
        When the user edits a footer menu
        And the user clicks "Publish page"
        And the user clicks "View Live"
        Then the preview of the footer menu is displayed with the edited data

    Scenario: Validation errors are raised when duplicate links are entered on the footer menu
        Given a CMS user logs into the admin site
        And pre-populated footer menu exists
        When user adds a duplicate link
        And the user clicks the "Save Draft" button
        Then an error message is displayed next to the duplicated link field

    Scenario: Validation errors are raised when footer menu is left empty
        Given a CMS user logs into the admin site
        When the user creates a footer menu
