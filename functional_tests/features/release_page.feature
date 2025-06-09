Feature: CMS users can draft, edit, and publish release pages

  Background:
    Given a contact details snippet exists
    And a superuser logs into the admin site
    And the user navigates to the release calendar page

  Scenario: A CMS user can choose from 30 minute intervals
    When the user clicks "Add child page" to create a new draft release page
    Then the time selection options are in 30 minute intervals

  Scenario: A CMS user can see a release date of today's date and 9:30 AM and datetime placeholders for the release page by textbox
    When the user clicks "Add child page" to create a new draft release page
    Then the a default release date time is today's date and 9:30 AM
    And the date placeholder, "YYYY-MM-DD HH:MM", is displayed in the date input textboxes

  Scenario: A CMS user can author and publish release page
    When the user clicks "Add child page" to create a new draft release page
    And the user sets the page status to "Published"
    And the user enters some example content on the page
    And looks up and selects a dataset
    And manually enters a dataset link
    And the user clicks "Publish"
    And the user clicks "View Live" on the publish confirmation banner
    Then the new published release page with the example content is displayed
    And the selected datasets are displayed on the page
    And the user can see the breadcrumbs

  Scenario Outline: A CMS user can add changes to release dates once the page is published
    When the user clicks "Add child page" to create a new draft release page
    And the user sets the page status to "<PageStatusd>"
    And the user enters some example content on the page
    And the user clicks "Publish"
    When user navigates to edit page
    And user adds date_change_log
    And the user clicks "Publish"
    And the user clicks "View Live" on the publish confirmation banner
    Then the release page displays the change in release date

    Examples:
      | PageStatusd |
      | Confirmed   |
      | Published   |
      | Cancelled   |

  Scenario: Release date text field is visible for provisional releases
    When the user clicks "Add child page" to create a new draft release page
    Then the page status is set to "Provisional" and the release date text field is visible

  Scenario Outline: Release date text field is hidden for provisional releases
    When the user clicks "Add child page" to create a new draft release page
    And the user sets the page status to "<PageStatus>"
    Then the date text field is not visible

    Examples:
      | PageStatus |
      | Confirmed  |
      | Published  |
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
