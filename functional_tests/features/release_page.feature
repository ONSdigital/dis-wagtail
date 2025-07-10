Feature: CMS users can draft, edit, and publish release pages

  Background:
    Given a superuser logs into the admin site
    And the user navigates to the release calendar page

  Scenario: Upon creation of a release page, several datetime features are available to users
    When the user clicks "Add child page" to create a new draft release page
    Then the default release date time is today's date and 9:30 AM
    And the date placeholder, "YYYY-MM-DD HH:MM", is displayed in the date input textboxes
    And the time selection options are in 30 minute intervals

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
# Release Calendar page creation

  Scenario: A CMS user creates and drafts a release calendar page
    When the user clicks "Add child page" to create a new draft release page
    And the user enters some example content on the page
    And the user clicks the "Save Draft" button
    And the user clicks the "Preview" button
    Then the "Provisional" page is displayed in the preview pane

  Scenario Outline: A CMS user can use preview mode to preview page at different statuses
    When the user clicks "Add child page" to create a new draft release page
    And the user enters "<PageStatus>" page content
    And the user clicks the "Save Draft" button
    And the user clicks the "Preview" button
    And the user changes preview mode to "<PageStatus>"
    Then the "<PageStatus>" page is displayed in the preview pane

    Examples:
      | PageStatus  |
      | Provisional |
      | Confirmed   |
      | Published   |
      | Cancelled   |

  Scenario Outline: User creates and publishes a release calendar page with different status
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
# Release date and next release date validations.

  Scenario: User adds contact details, publishes page and contact detail is displayed
    And a contact details snippet exists
    When the user clicks "Add child page" to create a new draft release page
    And the user sets the page status to "Confirmed"
    And the user enters some example content on the page
    And the user adds contact details
    And the user clicks "Publish"
    And the user clicks "View Live" on the publish confirmation banner
    Then the "Published" page is displayed
    And contact detail is displayed

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

  Scenario Outline: Release date text field is hidden for non-provisional releases
    When the user clicks "Add child page" to create a new draft release page
    And the user sets the page status to "<PageStatus>"
    Then the date text field is not visible

    Examples:
      | PageStatus |
      | Confirmed  |
      | Cancelled  |

  Scenario Outline: Validation error for invalid release date text
    When the user clicks "Add child page" to create a new draft release page
    And the user enters some example content on the page
    And the user adds a invalid <ReleaseDate> text
    And the user clicks "Publish"
    Then an error message is displayed describing invalid <ReleaseDate> text input

    Examples:
      | ReleaseDate       |
      | release date      |
      | next release date |

  Scenario Outline: Validation error when cancelled page is published without notice
    When the user clicks "Add child page" to create a new draft release page
    And the user enters some example content on the page
    And the user sets the page status to "Cancelled"
    And the user clicks "Publish"
    Then an error message is displayed describing notice must be added
# changes to release date

  Scenario Outline: User enters a change in release date, validation error is raised
    When the user clicks "Add child page" to create a new draft release page
    And the user enters some example content on the page
    And the user sets the page status to "Confirmed"
    And the user clicks "Publish"
    Then an error message is displayed describing that a date change log is needed

  Scenario: Validation error when next release date is before the release date
    When the user clicks "Add child page" to create a new draft release page
    And the user enters some example content on the page
    And adds the next release date before the release date
    And the user clicks "Publish"
    Then an error validation is raised to say you cannot do this

  Scenario: Validation error when next release date and release date text is entered
    When the user clicks "Add child page" to create a new draft release page
    And the user enters some example content on the page
    And the user enters both next release date and next release date text
    And the user clicks "Publish"
    Then an error validation is raised to say you cannot have both
# Pre-release access checks

  Scenario: Validation error when more than one description added on Pre-release Access
    When the user clicks "Add child page" to create a new draft release page
    And the user enters some example content on the page
    And multiple descriptions are added under pre-release access
    Then an error message is displayed about the descriptions

  Scenario: Validation error when more than one table added on Pre-release Access
    When the user clicks "Add child page" to create a new draft release page
    And the user enters some example content on the page
    And multiple tables are added under pre-release access
    And the user clicks "Publish"
    Then an error message is displayed about the tables

  Scenario: User adds pre-release access and related links to the page
    When the user clicks "Add child page" to create a new draft release page
    And the user enters some example content on the page
    And the user adds pre-release access information
    And the user adds related links
    And the user clicks "Publish"
    And the user clicks "View Live" on the publish confirmation banner
    Then the pre-release access is displayed
    And the related links is displayed

  Scenario: A CMS user cannot delete a release date change once the release page is published
    When the user clicks "Add child page" to create a new draft release page
    And the user enters some example content on the page
    And the user clicks "Publish"
    And the user returns to editing the release page
    And the user adds a release date change
    And the user clicks "Publish"
    And the user returns to editing the release page
    Then the user cannot delete the release date change

  Scenario: A CMS user cannot add multiple release date changes at a time
    When the user clicks "Add child page" to create a new draft release page
    And the user enters some example content on the page
    And the user clicks "Publish"
    And the user returns to editing the release page
    And the user adds a release date change
    And the user adds another release date change
    And the user clicks "Publish"
    Then the user sees a validation error message about adding multiple release date changes

  Scenario: A CMS user can add another release date change after the first one is published
    When the user clicks "Add child page" to create a new draft release page
    And the user enters some example content on the page
    And the user clicks "Publish"
    And the user returns to editing the release page
    And the user adds a release date change
    And the user clicks "Publish"
    And the user returns to editing the release page
    And the user adds another release date change
    And the user clicks the "Save Draft" button
    Then the release calendar page is successfully updated
    # Done twice on purpose to check validation is working
    When the user clicks the "Save Draft" button
    Then the release calendar page is successfully updated
    When the user clicks "Publish"
    Then the release calendar page is successfully published
