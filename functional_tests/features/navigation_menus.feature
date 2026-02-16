Feature: CMS users can manage navigation menus via the Wagtail admin interface

    Background:
        Given a Publishing Admin logs into the admin site

    # Footer Menu Creation and Basic Actions
    Scenario: A publishing admin edits a footer menu under Snippets
        When the user opens an existing footer menu for editing
        And  the user populates the footer menu with an internal link
        And  the user clicks the "Save draft" button
        And  the user clicks toggle preview
        Then the footer menu is displayed on the preview pane with an internal link

    Scenario: A publishing admin edits and publishes a footer menu
        When the user opens an existing footer menu for editing
        And the footer menu is populated with 3 columns
        And the user clicks "Publish"
        Then a banner confirming changes is displayed
        And the footer menu appears on the home page

    Scenario: A publishing admin sees the main menu rendered correctly on the home page
        Given the main menu is populated with columns, sections, and topic links
        When the publishing admin visits the home page
        Then the main menu displays the configured columns, sections, and topic links

    # Field Validation and Error Handling
    Scenario: Validation error when footer menu is left empty
        When the user opens an existing footer menu for editing
        And the user inserts an empty column block
        And the user clicks the "Save draft" button
        Then an error message is displayed preventing saving an empty column block

    Scenario: Validation error for duplicate links
        When the user opens an existing footer menu for editing
        And the user populates the footer menu with duplicate links
        And the user clicks the "Save draft" button
        Then an error message is displayed for duplicate links

    Scenario: Validation error for missing title on external URL
        When the user opens an existing footer menu for editing
        And the user adds a link with no title
        And the user clicks the "Save draft" button
        Then an error message is displayed about the missing title

    Scenario: Validation error for malformed URL
        When the user opens an existing footer menu for editing
        And the user adds a malformed URL
        And the user clicks the "Save draft" button
        Then an error message is displayed about the URL format

    Scenario: Validation error when more than 3 columns are added
        When the user opens an existing footer menu for editing
        And the user adds more than 3 columns
        And the user clicks the "Save draft" button
        Then an error message is displayed about column limit

    Scenario: Validation error when more than 10 links are added
        When the user opens an existing footer menu for editing
        And the user adds more than 10 links
        And the user clicks the "Save draft" button
        Then an error message is displayed about the link limit
