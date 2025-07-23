Feature: CMS user can manage changes to release date on the release calendar page

  Background:
    Given a superuser logs into the admin site
    And the user navigates to the release calendar page

# Changes to release date

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
