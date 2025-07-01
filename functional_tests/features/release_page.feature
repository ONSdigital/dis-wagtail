Feature: CMS users can draft, edit, and publish release pages

  Background:
    Given a contact details snippet exists
    And a superuser logs into the admin site
    And the user navigates to the release calendar page
# page features

  Scenario: Upon creation of a release page, several datetime features are available to users
    When the user clicks "Add child page" to create a new draft release page
    Then the default release date time is today's date and 9:30 AM
    And the date placeholder, "YYYY-MM-DD HH:MM", is displayed in the date input textboxes
    And the time selection options are in 30 minute intervals
  # datetime

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
    And the user enters some example content on the page
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

  Scenario Outline: User creates and publishes a release calendar page with the different status
    When the user clicks "Add child page" to create a new draft release page
    And the user sets the page status to "<PageStatus>"
    And the user enters some example content on the page
    And the user clicks "Publish"
    Then the user clicks "View Live" on the publish confirmation banner
    And the "<PageStatus>" page is displayed
    # All fail - Check what is missing in content - notice and such

    Examples:
      | PageStatus  |
      | Provisional |
      | Confirmed   |
      | Cancelled   |
# Release date and next release date validations.

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

  Scenario Outline: User cannot input invalid release date text
    When the user clicks "Add child page" to create a new draft release page
    And the user enters some example content on the page
    And the user adds a invalid <ReleaseDate> text
    And the user clicks "Publish"
    Then an error message is displayed describing invalid <ReleaseDate> text input

    Examples:
      | ReleaseDate       |
      | release date      |
      | next release date |

  Scenario Outline: User publishes a cancelled page, they must enter a notice
    When the user clicks "Add child page" to create a new draft release page
    And the user enters some example content on the page
    And the user sets the page status to "Cancelled"
    And the user clicks <Action>
    Then an error message is displayed describing notice must be added

    Examples:
      | Action                  |
      | "Publish"               |
      | the "Save Draft" button |
# changes to release date

  Scenario: User enters a change in release date, validation error is raised
    When the user clicks "Add child page" to create a new draft release page
    And the user enters some example content on the page
    And the user sets the page status to "Confirmed"
    And the user clicks "Publish"
  # may add draft too
    Then an error message is displayed describing that a date change log is needed

  Scenario: User enters the next release date which is before the release date
    When the user clicks "Add child page" to create a new draft release page
    And the user enters some example content on the page
    And adds the next release date before the release date
    And the user clicks "Publish"
    Then an error validation is raised to say you cannot do this

  Scenario: User enters the next release date and release date text
    When the user clicks "Add child page" to create a new draft release page
    And the user enters some example content on the page
    And the user enters both next release date and next release date text
    And the user clicks "Publish"
    # failing: locator not found
    Then an error validation is raised to say you cannot have both
#locale?
# Clean notice?
# Choosing contact details (will need the creation of an instance of contact within Snippets).
# Pre-release access checks.
# Related links checks
