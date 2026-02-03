Feature: CMS users can manage footer menus via the Wagtail admin interface

    Background:
        Given a CMS user logs into the admin site

    # Footer Menu Creation and Basic Actions
    Scenario: User creates a footer menu under Snippets
        When the user creates a footer menu instance
        And  the user populates the footer menu with an internal link
        And  the user clicks the "Save draft" button
        And  the user clicks toggle preview
        Then the footer menu is displayed on the preview pane with an internal link

    Scenario: User creates and publishes a footer menu
        When the user creates a footer menu instance
        And the user populates the footer menu with an external link
        And the user clicks "Publish"
        Then a banner confirming changes is displayed

    Scenario: User creates and previews a populated footer menu
        When the user creates a footer menu instance
        And the user populates the footer menu with an external link
        And the user clicks the "Save draft" button
        And the user clicks toggle preview
        Then the footer menu is displayed on the preview pane with an external link

    # Navigation Settings Integration and Verification
    Scenario: Footer menu can be saved via Navigation Settings and appears on the live home page
        When the user creates a footer menu instance
        And a footer menu is populated with 3 columns
        And the user clicks "Publish"
        And the user navigates to navigation settings
        And the user selects the footer menu
        And the user clicks "Save" to save the Snippet
        And the footer menu is saved successfully
        Then the footer menu appears on the home page

    # Field Validation and Error Handling
    Scenario: Validation error when footer menu is left empty
        When the user creates a footer menu instance
        And the user inserts an empty column block
        And the user clicks the "Save draft" button
        Then an error message is displayed preventing saving an empty column block

    Scenario: Validation error for duplicate links
        When the user creates a footer menu instance
        And the user populates the footer menu with duplicate links
        And the user clicks the "Save draft" button
        Then an error message is displayed for duplicate links

    Scenario: Validation error for missing title on external URL
        When the user creates a footer menu instance
        And the user adds a link with no title
        And the user clicks the "Save draft" button
        Then an error message is displayed about the missing title

    Scenario: Validation error for malformed URL
        When the user creates a footer menu instance
        And the user adds a malformed URL
        And the user clicks the "Save draft" button
        Then an error message is displayed about the URL format

    Scenario: Validation error when more than 3 columns are added
        When the user creates a footer menu instance
        And the user adds more than 3 columns
        And the user clicks the "Save draft" button
        Then an error message is displayed about column limit

    Scenario: Validation error when more than 10 links are added
        When the user creates a footer menu instance
        And the user adds more than 10 links
        And the user clicks the "Save draft" button
        Then an error message is displayed about the link limit

    # Deletion and Confirmation
    Scenario: User can delete a footer menu instance
        Given a footer menu exists
        When the user navigates to Snippets
        And the user clicks on "Footer menus"
        And the user selects "More options for Footer Menu"
        And the user clicks "Delete Footer Menu"
        Then a banner confirming the deletion is displayed
