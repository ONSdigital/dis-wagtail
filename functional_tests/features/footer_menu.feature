Feature: CMS users can create the footer menu
    
    Scenario: A CMS user can create and save a footer menu instance under Snippets
        Given a CMS user logs into the admin site
        When the user creates a footer menu instance
        And the user populates the footer menu
        And the user clicks the "Save Draft" button
        And the user clicks "View Live" from the preview
        Then the preview of the footer menu is displayed with the populated data
    
    Scenario: A CMS user can create and publish a footer menu under Snippets
        Given a CMS user logs into the admin site
        When the user creates a footer menu instance
        And the user populates the footer menu
        And the user clicks "Publish" the footer menu
        Then a banner confirming changes is displayed

    Scenario: a CMS user can select and configure the footer menu in Navigation settings.
        Given a CMS user logs into the admin site
        And a footer menu exists
        When a CMS user navigates to "Navigation settings"
        And the user selects footer menu in "Navigation settings"
        And the user clicks "saves" in the "Navigation Settings"
        Then the footer menu is configured

    Scenario: Validation errors are raised when footer menu is left empty
        Given a CMS user logs into the admin site
        When the user creates a footer menu instance
        And the user inserts an empty column block
        And the user clicks the "Save Draft" button
        Then an error message confirming the footer cannot be saved is displayed

    Scenario: Validation errors are raised when duplicate links are entered on the footer menu
        Given a CMS user logs into the admin site
        When the user creates a footer menu instance
        And the user populates the footer menu
        And the user enters duplicate information
        And the user clicks the "Save Draft" button
        Then an error message confirming the footer cannot be saved is displayed

    Scenario: Validation errors are raised when an external_url with no title is submitted
        Given a CMS user logs into the admin site
        When the user creates a footer menu instance
        And the user populates the footer menu
        And the user enters a link with no title
        And the user clicks the "Save Draft" button
        Then an error message confirming the footer cannot be saved is displayed

    Scenario: Validation errors are raised with an incorrect url submitted
        Given a CMS user logs into the admin site
        When the user creates a footer menu instance
        And the user populates the footer menu
        And the user enters an incorrect url
        And the user clicks the "Save Draft" button
        Then an error message confirming the footer cannot be saved is displayed
    
    Scenario: Validation errors are raised when more than 3 columns added
        Given a CMS user logs into the admin site
        When the user creates a footer menu instance
        And the user populates the footer menu
        And the user enters more than 3 columns
        And the user clicks the "Save Draft" button
        Then an error message and maximum number of column notification is displayed

    Scenario: Validation errors are raised when more than 10 links are added
        Given a CMS user logs into the admin site
        When a populated footer menu has been created
        And the user adds above the maximum links
        And the user clicks the "Save Draft" button
        Then an error message confirming the footer cannot be saved is displayed

    Scenario: A CMS user can add a link to an existing footer menu
        Given a CMS user logs into the admin site
        When the user creates a footer menu instance
        And the user populates the footer menu
        And the user clicks "Publish" the footer menu
        And the user navigates to edit the footer menu
        And the user adds an additional link to a footer menu
        And the user clicks the "Save Draft" button
        And the user clicks "View Live" from the preview
        Then the preview of the footer menu is displayed with the additional link

    Scenario: A CMS user can delete a link from an existing footer menu
        Given a CMS user logs into the admin site
        When the user creates a footer menu instance
        And the user populates the footer menu
        And the user adds an additional link to a footer menu
        And the user clicks the "Save Draft" button
        And the user deletes the additional link
        Then the preview does not show the deleted link

    Scenario: A CMS user can edit item to an existing footer menu
        Given a CMS user logs into the admin site
        When the user creates a footer menu instance
        And the user populates the footer menu
        And the user clicks "Publish" the footer menu
        And the user navigates to edit the footer menu
        And the user edits data on a pre existing footer menu
        And the user clicks the "Save Draft" button
        And the user clicks "View Live" from the preview
        Then the preview of the footer menu is displayed with the edited data
    
    Scenario: A CMS user can add a column to an existing footer menu
        Given a CMS user logs into the admin site
        When the user creates a footer menu instance
        And the user populates the footer menu
        And the user adds an additional column and link
        And the user clicks the "Save Draft" button
        And the user clicks "View Live" from the preview
        Then the preview will show the new column is added

    Scenario: A CMS user can delete a column in an existing footer menu
        Given a CMS user logs into the admin site
        When a populated footer menu has been created
        And the user adds an additional column and link
        And the user clicks the "Save Draft" button
        And the user deletes a column
        And the user clicks the "Save Draft" button
        And the user clicks "View Live" from the preview
        Then the preview will not show the deleted column

    Scenario: A CMS user can delete a footer menu instance
        Given a footer menu exists
        And a CMS user logs into the admin site
        When user deletes the footer menu
        Then a banner confirming changes is displayed

    Scenario: The footer menu is present at the home page
        Given a CMS user logs into the admin site
        When a populated footer menu has been created
        And the user clicks the "Save Draft" button
        And the user configures the footer menu in navigation settings
        Then the user navigates to the home page to see changes
