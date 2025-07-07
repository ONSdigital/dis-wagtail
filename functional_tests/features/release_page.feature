Feature: CMS users can draft, edit, and publish release pages

  Background:
    Given a contact details snippet exists
    And a superuser logs into the admin site
    And the user navigates to the release calendar page

  Scenario: Upon creation of a release page, several datetime features are available to users
    When the user clicks "Add child page" to create a new draft release page
    Then the default release date time is today's date and 9:30 AM
    And the date placeholder, "YYYY-MM-DD HH:MM", is displayed in the date input textboxes
    And the time selection options are in 30 minute intervals

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

  Scenario Outline: Release date text field is hidden for provisional releases
    When the user clicks "Add child page" to create a new draft release page
    And the user sets the page status to "<PageStatus>"
    Then the date text field is not visible

    Examples:
      | PageStatus |
      | Confirmed  |
      | Cancelled  |

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
