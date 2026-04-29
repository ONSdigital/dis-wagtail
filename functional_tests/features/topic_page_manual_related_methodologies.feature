Feature: A CMS user can manually manage related methodologies on a Topic Page

    Background:
        Given a superuser logs into the admin site
        And a topic page exists under the homepage
        And the topic page has at least 3 child methodologies

    Scenario: A user can add an external related methodology
        When the user edits the topic page
        And the user adds an external related methodology with title "External Methodology 1"
        And the user clicks the "Save draft" button
        And the user views the topic page draft
        Then the user can see "External Methodology 1" in the related methodologies section

    Scenario: Manually added links appear above auto-populated links
        When the user edits the topic page
        And the user adds an external related methodology with title "Manual Link"
        And the user clicks the "Save draft" button
        And the user views the topic page draft
        Then the related methodology "Manual Link" is the first in the list

    Scenario: Adding one manual link keeps two auto-populated links
        When the user edits the topic page
        And the user adds an external related methodology with title "Sticky Link 1"
        And the user clicks the "Save draft" button
        And the user views the topic page draft
        Then the related methods section contains 3 methods
        And the related methodology "Sticky Link 1" is the first in the list

    Scenario: Adding two manual links keeps one auto-populated link
        When the user edits the topic page
        And the user adds an external related methodology with title "Sticky Link 1"
        And the user adds an external related methodology with title "Sticky Link 2"
        And the user clicks the "Save draft" button
        And the user views the topic page draft
        Then the related methods section contains 3 methods
        And the related methodology "Sticky Link 1" is the first in the list
        And the related methodology "Sticky Link 2" is the second in the list
#
    Scenario: Adding three manual links removes all auto-populated links
        When the user edits the topic page
        And the user adds an external related methodology with title "Sticky Link 1"
        And the user adds an external related methodology with title "Sticky Link 2"
        And the user adds an external related methodology with title "Sticky Link 3"
        And the user clicks the "Save draft" button
        And the user views the topic page draft
        Then the related methods section contains only the 3 manually added methods

    Scenario: Deleting a manual link tops up the list with an auto-populated link
        Given the user has added one external related method to the topic page
        When the user edits the topic page
        And the user removes the first manually added related method
        And the user clicks the "Save draft" button
        And the user views the topic page draft
        Then the related methods section contains 3 auto-populated methods

    Scenario: A user can add an internal page with a custom title
        When the user edits the topic page
        And the user adds an internal related methodology with custom title "Custom Article Title"
        And the user clicks the "Save draft" button
        And the user views the topic page draft
        Then the user can see "Custom Article Title" in the related methods section
        And the custom title overrides the methods's original title

    Scenario: A user can specify the content type of manual links
        When the user edits the topic page
        And the user adds an external related methodology with content type "Information" and title "Sticky Link 1"
        And the user adds an external related methodology with content type "Article" and title "Sticky Link 2"
        And the user adds an external related methodology with content type "Methodology" and title "Sticky Link 3"
        And the user clicks the "Save draft" button
        And the user views the topic page draft
        Then the user can see item "Sticky Link 1" with content type "INFORMATION" in the related methodologies section
        Then the user can see item "Sticky Link 2" with content type "ARTICLE" in the related methodologies section
        Then the user can see item "Sticky Link 3" with content type "METHODOLOGY" in the related methodologies section
