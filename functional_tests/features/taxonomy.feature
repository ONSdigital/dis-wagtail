Feature: Users can tag pages with topics

    Scenario Outline: Theme and Topic pages can be tagged with a single topic
        Given a superuser logs into the admin site
        And a topic exists
        When the user tries to create a new <page> page
        And the user fills in the required <page> page content
        Then the user can link the page to the existing topic in the taxonomy editor tab
        And the user can successfully publish the page

        Examples:
            | page  |
            | theme |
            | topic |

    Scenario Outline: Theme and Topic pages have exclusive, one to one topic tags
        Given a superuser logs into the admin site
        And a topic exists
        And the topic is already linked to an existing <existing page> page
        When the user tries to create a new <new page> page
        Then the topic which is linked already exclusively linked does not show in the page taxonomy topic chooser

        Examples:
            | existing page | new page |
            | theme         | theme    |
            | theme         | topic    |
            | topic         | theme    |
            | topic         | topic    |

    Scenario: Other page types, for example the information page, can be tagged with multiple topics
        Given a superuser logs into the admin site
        And two topics exist
        When the user tries to create a new information page
        Then the user can tag the page with both topics in the taxonomy editor tab
