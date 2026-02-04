Feature: CMS users can create, configure, and manage release calendar pages, including handling edge cases and validation for invalid or incomplete input data

  Background:
    Given a contact details snippet exists
    And a superuser logs into the admin site
    And the user navigates to the release calendar page

  Scenario: A CMS user sees default release date, time placeholder, and 30-minute intervals when editing a release calendar page
    When the user clicks "Add child page" to create a new draft release calendar page
    Then today's date and 9:30 AM are set as the default in the release date input field
    And the datetime placeholder, "YYYY-MM-DD HH:MM", is displayed in the release date input field
    And the time selection dropdown displays options in 30-minute intervals

  Scenario Outline: A CMS user inputs a datetime on a release calendar page, the correct period is displayed
    Given a release calendar page exists
    When the user edits the release calendar page
    And the user inputs a <MeridiemIndicator> datetime
    And the user clicks the "Save draft" button
    And the user views the release calendar page draft
    Then the datetime is displayed with "<MeridiemIndicator>"

    Examples:
      | MeridiemIndicator |
      | am                |
      | pm                |

  Scenario Outline: A CMS user can create and publish a release calendar page with different statuses
    Given a release calendar page exists
    When the user edits the release calendar page
    And  the user sets the page status to "<PageStatus>"
    And  the user enters "<PageStatus>" page content
    And  the release calendar page goes through the publishing steps with superuser as user and Publishing Officer as reviewer
    And  the user clicks "View Live" on the publish confirmation banner
    Then the "<PageStatus>" page is displayed

    Examples:
      | PageStatus  |
      | Provisional |
      | Confirmed   |
      | Cancelled   |

  Scenario Outline: A CMS user can use preview modes to preview the page at different statuses
      When the user clicks "Add child page" to create a new draft release calendar page
      And the user enters "<PageStatus>" page content
      And the user clicks the "Save draft" button
      And the user opens the preview in a new tab, using the "<PageStatus>" preview mode
      Then the "<PageStatus>" page is displayed in the preview tab

      Examples:
        | PageStatus |
        | Provisional |
        | Confirmed   |
        | Published   |
        | Cancelled   |

  Scenario Outline: A CMS user adds <Feature> to a release calendar page and verifies their display in the Published preview tab
    When the user clicks "Add child page" to create a new draft release calendar page
    And the user enters some example content on the page
    And the user adds <Feature> to the release calendar page
    And the user clicks the "Save draft" button
    And the user opens the preview in a new tab, using the "Published" preview mode
    Then the example content is displayed in the preview tab
    And <Feature> is displayed in the release calendar page preview tab

    Examples:
      | Feature                        |
      | a release date text            |
      | a next release date text       |
      | a related link                 |
#      | pre-release access information |


# Checks visibility of release date text field based on page status (Provisional vs. others) in the admin interface.
  Scenario: A CMS user can see release date text field for a provisional release calendar page
    When the user clicks "Add child page" to create a new draft release calendar page
    Then the page status is set to "Provisional" and the release date text field is visible

  Scenario Outline: Release date text field is hidden for non-provisional releases
    When the user clicks "Add child page" to create a new draft release calendar page
    And the user sets the page status to "<PageStatus>"
    Then the date text field is not visible

    Examples:
      | PageStatus |
      | Confirmed  |
      | Cancelled  |

  Scenario Outline: Validation errors are shown when a user enters invalid release date information
    When the user clicks "Add child page" to create a new draft release calendar page
    And the user enters some example content on the page
    And the user adds <Input> to the release calendar page
    And the user clicks the "Save draft" button
    Then an error message is displayed to say the page could not be created
    And the user sees a validation error message: <Error>

    Examples:
      | Input                                                                | Error                                                         |
      | an invalid release date text                                         | invalid release date text input                               |
      | an invalid next release date text                                    | invalid next release date text input                          |
      | the next release date is set to a date earlier than the release date | next release date cannot be before release date               |
      | both next release date and next release date text                    | cannot have both next release date and next release date text |

  Scenario: Validation error is shown when publishing a cancelled release calendar page without a cancellation notice
    When the user clicks "Add child page" to create a new draft release calendar page
    And the user sets the page status to "Cancelled"
    And the user enters some example content on the page
    And the user clicks the "Save draft" button
    Then an error message is displayed to say the page could not be created
    And the user sees a validation error message: a cancellation notice must be added

  Scenario Outline: Validation errors are shown when invalid pre-release access information is provided
    When the user clicks "Add child page" to create a new draft release calendar page
    And the user enters some example content on the page
    And <Feature> <is/are> added under pre-release access
    And the user clicks the "Save draft" button
    Then an error message is displayed to say the page could not be created
    And the user sees a validation error message: <Error>

    Examples:
      | Feature                               | is/are | Error                        |
      | multiple descriptions                 | are    | maximum descriptions allowed |
      | multiple tables                       | are    | maximum tables allowed       |
      | a table with no table header selected | is     | unselected options           |
      | an empty table                        | is     | empty tables are not allowed |

  Scenario: A CMS user can add a date change log, under changes to release date, and preview it in the published preview tab
    Given a "Confirmed" published release calendar page exists
    When the user edits the release calendar page
    And  the user changes the release date to a new date
    And  the user adds a date change log to the release calendar page
    And  the user opens the preview in a new tab, using the "Published" preview mode
    Then the example content is displayed in the preview tab
    And  a release date change is displayed in the release calendar page preview tab

  Scenario: The previous date in the date change log block is pre-populated
    Given a "Confirmed" published release calendar page exists
    When the user edits the release calendar page
    And the user changes the release date to a new date
    And the user adds a date change log to the release calendar page
    Then the previous date field is pre-populated with the old release date

  Scenario: The Changes to release date block is not shown when creating a new page
    When the user clicks "Add child page" to create a new draft release calendar page
    Then the Changes to release date block is not visible

  Scenario: The previous date field in the date change log block is uneditable
    Given a "Confirmed" published release calendar page exists
    When the user edits the release calendar page
    And  the user adds a date change log to the release calendar page
    Then the previous release date field is not editable

  Scenario: A CMS user cannot delete a date change log that has been published
    Given a "Confirmed" published release calendar page with a date change log exists
    When the user edits the release calendar page
    Then the user cannot delete the date change log

  Scenario: Validation error is raised when multiple date change logs are added
    Given a "Confirmed" published release calendar page exists
    When the user edits the release calendar page
    And  the user changes the release date to a new date
    And  the user adds multiple date change logs under changes to release date
    And  the user clicks the "Save draft" button
    Then an error message is displayed to say the page could not be saved
    And  the user sees a validation error message: multiple release date change logs

  Scenario Outline: Validation errors are raised when release date changes and date change log fields are inconsistent on a confirmed page
    Given a "Confirmed" published release calendar page exists
    When the user edits the release calendar page
    And  the user adds a <DateChangeLogValidationError> under changes to release date
    And  the user clicks the "Save draft" button
    Then an error message is displayed to say the page could not be saved
    And  the user sees a validation error message: <DateChangeLogValidationError>

    Examples:
      | DateChangeLogValidationError                 |
      | release date change with no date change log  |
      | date change log with no release date change  |

Scenario: A CMS user can add another date change log after the first one is published
    Given a "Confirmed" published release calendar page exists
    When the user edits the release calendar page
    And the user changes the release date to a new date
    And the user adds a date change log to the release calendar page
    And the release calendar page goes through the publishing steps with superuser as user and Publishing Admin as reviewer
    And the user returns to editing the published page
    And the user changes the release date to a new date again
    And the user adds another date change log under changes to release date
    Then the user can save the page
    # Done twice on purpose to check validation is working
    Then the user can save the page
    When the release calendar page goes through the publishing steps with superuser as user and Publishing Admin as reviewer
    Then the page is published
