Feature: A CMS user can manually manage related articles on a Topic Page

    Background:
        Given a superuser logs into the admin site
        And a topic page exists under the homepage
        And the topic page has at least 3 series with a statistical article

    Scenario: A user can add an external related article
        When the user edits the topic page
        And the user adds an external related article with title "External Article 1" and a short description
        And the user clicks the "Save draft" button
        And the user views the topic page draft
        Then the user can see "External Article 1" in the related articles section

    Scenario: Manually added links appear above auto-populated links
        When the user edits the topic page
        And the user adds an external related article with title "Manual Link" and a short description
        And the user clicks the "Save draft" button
        And the user views the topic page draft
        Then the related article "Manual Link" appears at the top of the list

    Scenario: Adding one manual link keeps two auto-populated links
        When the user edits the topic page
        And the user adds an external related article with title "Sticky Link 1" and a short description
        And the user clicks the "Save draft" button
        And the user views the topic page draft
        Then the related articles section contains 3 articles
        And the related article "Sticky Link 1" is the first in the list

    Scenario: Adding two manual links keeps one auto-populated link
        When the user edits the topic page
        And the user adds an external related article with title "Sticky Link 1" and a short description
        And the user adds an external related article with title "Sticky Link 2" and a short description
        And the user clicks the "Save draft" button
        And the user views the topic page draft
        Then the related articles section contains 3 articles
        And the related article "Sticky Link 1" is the first in the list
        And the related article "Sticky Link 2" is the second in the list

    Scenario: Adding three manual links removes all auto-populated links
        When the user edits the topic page
        And the user adds an external related article with title "Sticky Link 1" and a short description
        And the user adds an external related article with title "Sticky Link 2" and a short description
        And the user adds an external related article with title "Sticky Link 3" and a short description
        And the user clicks the "Save draft" button
        And the user views the topic page draft
        Then the related articles section contains only the 3 manually added articles

    Scenario: Deleting a manual link tops up the list with an auto-populated link
        Given the user has added one external related article to the topic page
        When the user edits the topic page
        And the user removes the first manually added related article
        And the user clicks the "Save draft" button
        And the user views the topic page draft
        Then the related articles section contains 3 auto-populated articles

    Scenario: A user can add an internal page with a custom title
        When the user edits the topic page
        And the user adds an internal related article with custom title "Custom Article Title"
        And the user clicks the "Save draft" button
        And the user views the topic page draft
        Then the user can see "Custom Article Title" in the related articles section
        And the custom title overrides the page's original title
