Feature: CMS users can manage footer menus via the Wagtail admin interface

    Background:
        Given a CMS user logs into the admin site

    # Footer Menu Creation and Basic Actions
    Scenario: User creates a footer menu under Snippets
        When the user creates a footer menu instance
        And the user populates the footer menu with a page
        And the user clicks the "Save Draft" button
        And the user clicks the "Preview" button
        Then the footer menu is displayed on the preview pane

    Scenario: User creates and publishes a footer menu
        When the user creates a footer menu instance
        And the user populates the footer menu
        And the user clicks "Publish page"
        Then a banner confirming changes is displayed

    # Navigation Settings Integration
    Scenario: Footer menu can be configured via Navigation Settings
        Given a footer menu exists
        When the user navigates to navigation settings
        And the user selects the footer menu
        And the user clicks "Save" to save the Snippet
        Then the footer menu is configured successfully

    # Field Validation and Error Handling
    Scenario: Validation error when footer menu is left empty
        When the user creates a footer menu instance
        And the user inserts an empty column block
        And the user clicks the "Save Draft" button
        Then an error message is displayed preventing saving an empty column block

    Scenario: Validation error for duplicate links
        When the user creates a footer menu instance
        And the user populates the footer menu with duplicate links
        And the user clicks the "Save Draft" button
        Then an error message is displayed for duplicate links

    Scenario: Validation error for missing title on external URL
        When the user creates a footer menu instance
        And the user adds a link with no title
        And the user clicks the "Save Draft" button
        Then an error message is displayed about the missing title

    Scenario: Validation error for malformed URL
        When the user creates a footer menu instance
        And the user adds a malformed URL
        And the user clicks the "Save Draft" button
        Then an error message is displayed about the URL format

    Scenario: Validation error when more than 3 columns are added
        When the user creates a footer menu instance
        And the user adds more than 3 columns
        And the user clicks the "Save Draft" button
        Then an error message is displayed about column limit

    Scenario: Validation error when more than 10 links are added
        When the user creates a footer menu instance
        And the user adds more than 10 links
        And the user clicks the "Save Draft" button
        Then an error message is displayed about the link limit

# # Deletion and Confirmation
# Scenario: User can delete a footer menu instance
#     Given a footer menu exists
#     When the user deletes the footer menu
#     Then a banner confirming the deletion is displayed

# # Final Verification
# Scenario: Footer menu appears on the live home page
#     When a populated footer menu is created and saved
#     And the user clicks the "Save Draft" button
#     And the user configures the footer menu in Navigation Settings
#     Then the footer menu appears on the home page
