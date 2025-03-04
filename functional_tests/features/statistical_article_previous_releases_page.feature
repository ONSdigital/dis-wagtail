Feature: For every article release there is a previous_release_page

    Scenario: External user can see the Statistical Article
        Given a topic page exists with status published
        And the topic page has a statistical article in a series with status published
        When an external user navigates to statistical article in a series previous releases page
        Then the external user should not see pagination



