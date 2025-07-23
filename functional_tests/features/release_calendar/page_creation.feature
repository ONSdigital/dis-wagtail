Feature: CMS users can draft, edit, and publish release pages

  Background:
    Given a superuser logs into the admin site
    And the user navigates to the release calendar page

# Preview modes

  Scenario Outline: A CMS user can use preview modes to preview the page at different statuses
    When the user clicks "Add child page" to create a new draft release page
    And the user enters "<PageStatus>" page content
    And the user clicks the "Save Draft" button
    And the user clicks the "Preview" button
    And the user changes preview mode to "<PageStatus>"
    And the preview tab is opened
    Then the "<PageStatus>" page is displayed in the preview tab

    Examples:
      | PageStatus  |
      | Provisional |
      | Confirmed   |
      | Published   |
      | Cancelled   |

# Publishing with statuses

  Scenario Outline: A CMS user creates and publishes a release calendar page with different status
    When the user clicks "Add child page" to create a new draft release page
    And the user sets the page status to "<PageStatus>"
    And the user enters "<PageStatus>" page content
    And the user clicks "Publish"
    And the user clicks "View Live" on the publish confirmation banner
    Then the "<PageStatus>" page is displayed

    Examples:
      | PageStatus  |
      | Provisional |
      | Confirmed   |
      | Cancelled   |
    
# Previewing published release page with full content

  Scenario: A CMS User publishes a release page and the preview will display all added content
    Given a contact details snippet exists
    And a Release Calendar page with a published notice exists
    When the user navigates to the published release calendar page
    And the user adds a release date change
    And the user adds pre-release access information
    And the user adds contact details
    And the user adds related links
    And the user clicks the "Save Draft" button
    And the user clicks the "Preview" button
    And the user changes preview mode to "Published"
    And the preview tab is opened
    Then the release date change is displayed
    And contact detail is displayed
    And related links are displayed
    And the pre-release access information is displayed
  
# Cancelled notice

  Scenario: Validation error when cancelled page is published without notice
    When the user clicks "Add child page" to create a new draft release page
    And the user enters some example content on the page
    And the user sets the page status to "Cancelled"
    And the user clicks "Publish"
    Then an error message is displayed describing notice must be added

# Pre-release access validation

  Scenario: Validation error when more than one description added on pre-release Access
    When the user clicks "Add child page" to create a new draft release page
    And the user enters some example content on the page
    And multiple descriptions are added under pre-release access
    Then an error message is displayed about the descriptions

  Scenario: Validation error when more than one table added on pre-release Access
    When the user clicks "Add child page" to create a new draft release page
    And the user enters some example content on the page
    And multiple tables are added under pre-release access
    And the user clicks "Publish"
    Then an error message is displayed about the tables

