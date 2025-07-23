Feature: CMS users can input datetime features on a release calendar page

  Background:
    Given a superuser logs into the admin site
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

  Scenario Outline: Validation error with invalid release date text input
    When the user clicks "Add child page" to create a new draft release page
    And the user enters some example content on the page
    And the user adds an invalid <ReleaseDate> text
    And the user clicks "Publish"
    Then an error message is displayed describing invalid <ReleaseDate> text input

    Examples:
      | ReleaseDate       |
      | release date      |
      | next release date |

  Scenario: Validation error when next release date is before the release date
    When the user clicks "Add child page" to create a new draft release page
    And the user enters some example content on the page
    And adds the next release date before the release date
    And the user clicks "Publish"
    Then an error validation is raised to say next release date cannot be before release date

  Scenario: Validation error when next release date and next release date text is entered
    When the user clicks "Add child page" to create a new draft release page
    And the user enters some example content on the page
    And the user enters both next release date and next release date text
    And the user clicks "Publish"
    Then an error message says you cannot enter a next release date and a next release date text at the same time
