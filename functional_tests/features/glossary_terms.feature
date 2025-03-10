Feature: General use of Glossary Terms

Scenario: A CMS user can create a Glossary Term
    Given a CMS user logs into the admin site
    When the user adds a Glossary Terms snippet
    Then the Glossary Term is added to the list
    And the Updated time is displayed
    And the Updated by field is populated with the user's name
    And the Owner field is populated with the user's name
Scenario: A CMS user can access the past revisions of the Glossary Term
    Given a CMS user logs into the admin site
    And the user adds a Glossary Terms snippet 
    And the user modifies the Glossary Term description
    When the user navigates to the snippet history menu
    Then the past revisions of the snippet are displayed

Scenario: A CMS user can see the preview of the Glossary Term
    Given a CMS user logs into the admin site
    And the user fills in Glossary Term details
    When the user clicks the "Preview" button
    Then the user can see the preview of the Glossary Term

Scenario: The Glossary Term raise validation errors when name is duplicated
    Given a CMS user logs into the admin site
    And the user adds a Glossary Terms snippet 
    When the user adds another Glossary Terms snippet with the same name
    Then a validation error is displayed


Scenario: The user can add the Glossary Terms in a section of a page
    Given a topic page exists under a theme page
    And a CMS user logs into the admin site
    And the user adds a Glossary Terms snippet 
    When the user creates a methodology page as a child of the existing topic page
    And the user populates the methodology page
    And adds Glossary Terms to the page content
    When the user clicks the "Preview" button
    Then the user can see the preview of the Glossary Term
