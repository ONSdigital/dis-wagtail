Feature: CMS users can draft, edit, and publish release pages

  Background:
    Given a contact detail snippet exists
    And a superuser logs into the admin site
    And the user navigates to the release calendar page

# Time input features

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

# Release date and next release date validations

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

  Scenario Outline: Validation error with invalid release date inputs
    When the user clicks "Add child page" to create a new draft release page
    And the user enters some example content on the page
    And the user adds <input>
    And the user clicks "Publish"
    Then the user sees a validation error message about the <Error>

    Examples:
      | input                                             | Error                                           |
      | an invalid release date text                      | invalid release date text input                 |
      | an invalid next release date text                 | invalid next release date text input            |
      | the next release date before the release date     | next release date cannot be before release date |
      | both next release date and next release date text | next release date and next release date text    |

# Preview modes

 Scenario Outline: A CMS user can use preview modes to preview the page at different statuses
    When the user clicks "Add child page" to create a new draft release page
    And the user enters "<PreviewMode>" page content
    And the user clicks the "Save Draft" button
    And the user opens the preview in a new tab with a preview mode of "<PreviewMode>"
    Then the "<PreviewMode>" page is displayed in the preview tab

    Examples:
      | PreviewMode |
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

  Scenario Outline: A CMS User publishes a release page with a page feature
    Given a Release Calendar page with a published notice exists
    When the user navigates to the published release calendar page
    And the user adds <Feature>
    And the user clicks the "Save Draft" button
    And the user opens the preview in a new tab with a preview mode of "Published"
    Then <Feature> is displayed in the preview tab

    Examples:
      | Feature                        |
      | related link                   |
      | pre-release access information |
# Cancelled notice

  Scenario: Validation error when cancelled page is published without notice
    When the user clicks "Add child page" to create a new draft release page
    And the user enters some example content on the page
    And the user sets the page status to "Cancelled"
    And the user clicks "Publish"
    Then an error message is displayed describing notice must be added

# Prerelease Access

  Scenario Outline: Validation errors for pre-release Access
    When the user clicks "Add child page" to create a new draft release page
    And the user enters some example content on the page
    And <Feature> <is/are> added under pre-release access
    And the user clicks the "Save Draft" button
    Then an error message is displayed to say page could not be saved
    And the user sees a validation error message about the <Error>
    Examples:
      | Feature                             |is/are | Error             |
      | multiple descriptions               |are    | descriptions      |
      | multiple tables                     |are    | maximum tables    |
      | table with no table header selected |is     | unselected options|
      | empty table                         |is     | empty table       |
 

# Changes to release date

 Scenario: A CMS User publishes a release page with a change to release date
    Given a Release Calendar page with a published notice exists
    When the user navigates to the published release calendar page
    And the user adds a release date change
    And the user clicks the "Save Draft" button
    And the user opens the preview in a new tab with a preview mode of "Published"
    Then the release date change is displayed in the preview tab

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
   
Scenario: Validation error raised when there is a change in release date and no change log added
    When the user clicks "Add child page" to create a new draft release page
    And the user enters some example content on the page
    And the user sets the page status to "Confirmed"
    And the user clicks "Publish"
    And the user returns to editing the release page
    And the user edits this to have a different release date
    And the user clicks "Publish"
    Then an error message is displayed describing that a date change log is needed
