Feature: General use of Definitions

Scenario: A CMS user can create a Definition
    Given a superuser logs into the admin site
    When the user adds a Definition snippet
    Then the Definition is added to the list
    And the Updated time is displayed
    And the Updated by field is populated with the user's name
    And the Owner field is populated with the user's name

Scenario: A CMS user can access the past revisions of the Definition
    Given a superuser logs into the admin site
    And the user adds a Definition snippet
    And the user modifies the Definition description
    When the user navigates to the snippet history menu
    Then the past revisions of the snippet are displayed

Scenario: A CMS user can see the preview of the Definition
    Given a superuser logs into the admin site
    And the user fills in Definition details
    When the user clicks the "Preview" button
    Then the user can see the Definition in the preview tab
    And the user can click the Definition to see the definition in the preview tab

Scenario: The Definition raises validation errors when name is duplicated
    Given a superuser logs into the admin site
    And the user adds a Definition snippet
    When the user adds another Definition snippet with the same name
    Then a validation error is displayed

Scenario: The user can add Definitions in a section of a page
    Given a topic page exists under the homepage
    And a superuser logs into the admin site
    And a Definition snippet exists
    When the user creates a methodology page as a child of the existing topic page
    And the user populates the methodology page
    And adds Definitions to the page content
    And the user clicks "Publish"
    And the user clicks "View Live" on the publish confirmation banner
    Then the user can see the Definition
    And the user can click the Definition to see the definition
