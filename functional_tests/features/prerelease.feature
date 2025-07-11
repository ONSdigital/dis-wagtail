Feature: Pre-release

  Background:
    Given a superuser logs into the admin site
    And the user navigates to the release calendar page

  Scenario: A CMS User publishes a release page and the preview will will display all content
    And a Release Calendar page with a publish notice exists
    When the user navigates to the published release calendar page
    And the user adds a release date change
    And the user adds pre-release access information
    And the user clicks the "Save Draft" button
    And the user clicks the "Preview" button
    And the user changes preview mode to "Published"
    And the preview tab opened
    Then the pre-release access is displayed
