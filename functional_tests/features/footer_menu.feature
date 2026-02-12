Feature: CMS users can manage footer menus via the Wagtail admin interface

    # Footer Menu Creation and Basic Actions
    Scenario: A publishing admin edits a footer menu under Snippets
        Given a Publishing Admin logs into the admin site
        When the user opens an existing footer menu for editing
        And the user populates the footer menu with an internal link
        And the user clicks the "Save Draft" button
        And the user clicks the "Preview" button
        Then the footer menu is displayed on the preview pane with an internal link

    Scenario: User creates and publishes a footer menu
        Given a Publishing Admin logs into the admin site
        When the user opens an existing footer menu for editing
        And the user populates the footer menu with an external link
        And the user clicks "Publish"
        Then a banner confirming changes is displayed

    # Field Validation and Error Handling
    Scenario: Validation error when footer menu is left empty
        Given a Publishing Admin logs into the admin site
        When the user opens an existing footer menu for editing
        And the user inserts an empty column block
        And the user clicks the "Save Draft" button
        Then an error message is displayed preventing saving an empty column block

    Scenario: Validation error for duplicate links
        Given a Publishing Admin logs into the admin site
        When the user opens an existing footer menu for editing
        And the user populates the footer menu with duplicate links
        And the user clicks the "Save Draft" button
        Then an error message is displayed for duplicate links

    Scenario: Validation error for missing title on external URL
        Given a Publishing Admin logs into the admin site
        When the user opens an existing footer menu for editing
        And the user adds a link with no title
        And the user clicks the "Save Draft" button
        Then an error message is displayed about the missing title
    
    Scenario: Validation error for malformed URL
        Given a Publishing Admin logs into the admin site
        When the user opens an existing footer menu for editing
        And the user adds a malformed URL
        And the user clicks the "Save Draft" button
        Then an error message is displayed about the URL format

    Scenario: Validation error when more than 3 columns are added
        Given a Publishing Admin logs into the admin site
        When the user opens an existing footer menu for editing
        And the user adds more than 3 columns
        And the user clicks the "Save Draft" button
        Then an error message is displayed about column limit
    
    Scenario: Validation error when more than 10 links are added
        Given a Publishing Admin logs into the admin site
        When the user opens an existing footer menu for editing
        And the user adds more than 10 links
        And the user clicks the "Save Draft" button
        Then an error message is displayed about the link limit
