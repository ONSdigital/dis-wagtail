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
