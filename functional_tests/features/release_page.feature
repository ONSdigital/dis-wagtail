Feature: CMS users can draft, edit, and publish release pages

  Background:
    Given a contact detail snippet exists
    And a superuser logs into the admin site
    And the user navigates to the release calendar page

# Time input features

  Scenario: A CMS user has several datetime features available when editing the release calendar page
    When the user clicks "Add child page" to create a new draft release page
    Then the default release date time is today's date and 9:30 AM
    And the date placeholder, "YYYY-MM-DD HH:MM", is displayed in the date input textboxes
    And the time selection options are in 30 minute intervals

  Scenario Outline: When a CMS user inputs a datetime on a release calendar page, the correct period is displayed
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


  Scenario Outline: A CMS user can create and publish a release calendar page with different statuses
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

# Preview modes

 Scenario Outline: A CMS user can use preview modes to preview the page at different statuses
    When the user clicks "Add child page" to create a new draft release page
    And the user enters "<PreviewMode>" page content
    And the user clicks the "Save Draft" button
    And the user opens the preview in a new tab, using the "<PreviewMode>" preview mode
    Then the "<PreviewMode>" page is displayed in the preview tab

    Examples:
      | PreviewMode |
      | Provisional |
      | Confirmed   |
      | Published   |
      | Cancelled   |

  Scenario Outline: A CMS User can publish a release page with different page feature
    When the user clicks "Add child page" to create a new draft release page
    And the user enters some example content on the page
    And the user adds <Feature> to the release calendar page
    And the user clicks the "Save Draft" button
    And the user opens the preview in a new tab, using the "Published" preview mode
    Then the example content is displayed in the preview tab
    And <Feature> is displayed in the release calendar page preview tab

    Examples:
      | Feature                        |
      | a release date text            |
      | a next release date text       |
      | a related link                 |
      | pre-release access information |
      | a release date change          | 

# Release date and next release date validations

  Scenario: A CMS user can see release date text field for a provisional release page
    When the user clicks "Add child page" to create a new draft release page
    Then the page status is set to "Provisional" and the release date text field is visible

  Scenario Outline: Release date text field is hidden for non-provisional releases
    When the user clicks "Add child page" to create a new draft release page
    And the user sets the page status to "<PageStatus>"
    Then the date text field is not visible

    Examples:
      | PageStatus |
      | Confirmed  |
      | Cancelled  |

#orderd ^^
  Scenario Outline: Validation errors are raised when invalid release dates are entered
    When the user clicks "Add child page" to create a new draft release page
    And the user enters some example content on the page
    And the user adds <Input>
    And the user clicks "Publish"
    Then an error message is displayed to say page could not be saved
    And the user sees a validation error message: <Error>

    Examples:
      | Input                                               | Error                                                         |
      | an invalid release date text                        | invalid release date text input                               |
      | an invalid next release date text                   | invalid next release date text input                          |
      | the next release date to be before the release date | next release date cannot be before release date               |
      | both next release date and next release date text   | cannot have both next release date and next release date text |


# Cancelled notice

  Scenario: Validation error is raised when a cancelled page is published without a notice
    When the user clicks "Add child page" to create a new draft release page
    And the user sets the page status to "Cancelled"
    And the user enters some example content on the page
    And the user clicks "Publish"
    Then an error message is displayed to say page could not be saved
    And the user sees a validation error message: a notice must be added

# Prerelease Access

  Scenario Outline: Validation errors are raised when invalid data is input for pre-release Access
    When the user clicks "Add child page" to create a new draft release page
    And the user enters some example content on the page
    And <Feature> <is/are> added under pre-release access
    And the user clicks the "Save Draft" button
    Then an error message is displayed to say page could not be saved
    And the user sees a validation error message about the <Error>
    Examples:
      | Feature                               | is/are | Error                        |
      | multiple descriptions                 | are    | maximum descriptions allowed |
      | multiple tables                       | are    | maximum tables allowed       |
      | a table with no table header selected | is     | unselected options           |
      | an empty table                        | is     | empty table                  |
 

# Changes to release date
  Scenario: A CMS user cannot delete a release date change once the release page is published
    Given a Release Calendar page with a published notice exists
    When the user navigates to the published release calendar page
    And the user adds a release date change to the release calendar page
    And the user clicks "Publish"
    And the user returns to editing the published page
    Then the user cannot delete the release date change

  Scenario: Validation Errors are raised when multiple release date changes are added
    Given a Release Calendar page with a published notice exists
    When the user navigates to the published release calendar page
    And the user adds multiple release date changes 
    And the user clicks "Publish"
    Then the user sees a validation error message about the multiple release date changes

  Scenario: Validation Errors are raised when there is a release date change with no date change log added to a confirmed page
    Given a Release Calendar page with a published notice exists
    When the user navigates to the published release calendar page
    And the user sets the page status to "Confirmed"
    And the user clicks "Publish"
    When the user navigates to the published release calendar page
    And the user adds release date change with no date change log
    And the user clicks "Publish"
    Then the user sees a validation error message about the release date change with no date change log

  Scenario: A CMS user can add another release date change after the first one is published
    Given a Release Calendar page with a published notice exists
    When the user navigates to the published release calendar page
    And the user adds a release date change to the release calendar page
    And the user clicks "Publish"
    And the user returns to editing the published page
    And the user adds another release date change
    And the user clicks the "Save Draft" button
    Then the release calendar page is successfully updated
    # Done twice on purpose to check validation is working
    When the user clicks the "Save Draft" button
    Then the release calendar page is successfully updated
    When the user clicks "Publish"
    Then the release calendar page is successfully published
