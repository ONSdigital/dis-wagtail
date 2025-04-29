Feature: CMS users can draft, edit, and publish topic pages

    Scenario: A CMS user can feature an article series
        Given a superuser logs into the admin site
        And a topic page exists under a theme page
        And the topic page has a statistical article in a series
        When the user edits the topic page
        And the user clicks the "Choose Article Series page" button
        And the user selects the article series
        And publishes the page
        And the user visits the topic page
        Then the topic page with the example content is displayed
        And the user can see the topic page featured article

    Scenario: The featured series on a topic page displays the latest article
        Given a topic page exists under a theme page
        And the user has created a statistical article in a series
        And the user has featured the series
        When the user creates a new statistical article in the series
        And the user visits the topic page
        Then the user can see the newly created article in featured spot

    Scenario: A CMS user can choose headline figures when editing a topic page
        When the user goes to add a new statistical article page
        And the user adds basic statistical article page content
        And the user adds headline figures
        And the user clicks "Publish"
        And the user edits the ancestor topic
        And the user clicks to add headline figures to the topic page
        Then the headline figures are shown

    Scenario: A CMS user can add headline figures to a topic page
        When the user goes to add a new statistical article page
        And the user adds basic statistical article page content
        And the user adds headline figures
        And the user clicks "Publish"
        And the user edits the ancestor topic
        And the user adds two headline figures to the topic page
        And the user clicks "Publish"
        And the user clicks "View Live" on the publish confirmation banner
        Then the published topic page has the added headline figures
        And the headline figures on the topic page link to the statistical page

    Scenario: A CMS user can reorder headline figures on a topic page
        When the user goes to add a new statistical article page
        And the user adds basic statistical article page content
        And the user adds headline figures
        And the user clicks "Publish"
        And the user edits the ancestor topic
        And the user adds two headline figures to the topic page
        And the user clicks "Publish"
        And the user clicks "View Live" on the publish confirmation banner
        Then the published topic page has the added headline figures in the correct order
        And the user edits the ancestor topic
        When the user reorders the headline figures on the topic page
        And the user clicks "Publish"
        And the user clicks "View Live" on the publish confirmation banner
        Then the published topic page has reordered headline figures

    Scenario: A CMS user can reorder headline figures on a Statistical Article Page without affecting the order of the figures on the topic page
        When the user goes to add a new statistical article page
        And the user adds basic statistical article page content
        And the user adds headline figures
        And the user clicks "Publish"
        And the user edits the ancestor topic
        And the user adds two headline figures to the topic page
        And the user clicks "Publish"
        And the user clicks "View Live" on the publish confirmation banner
        Then the published topic page has the added headline figures in the correct order
        When the user returns to editing the statistical article page
        And the user reorders the headline figures on the Statistical Article Page
        And the user clicks "Publish"
        And the user views the topic page
        Then the published topic page has the added headline figures in the correct order
