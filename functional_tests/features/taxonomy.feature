Feature: Users can tag pages with topics

    Scenario Outline: Theme and Topic pages can be tagged with a single topic
        Given a CMS user logs into the admin site
        And a topic exists
        When the CMS user tries to create a new <page type> page
        Then the CMS user can link the page to the existing topic in the taxonomy editor tab

        Examples:
            | page type |
            | theme     |
            | topic     |

    Scenario Outline: Theme and Topic pages have exclusive, one to one topic tags
        Given a CMS user logs into the admin site
        And a topic exists
        And the topic is already linked to an existing <existing page type> page
        When the CMS user tries to create a new <new page type> page
        Then they cannot select the topic which is already linked to the other exclusive page

        Examples:
            | existing page type | new page type |
            | theme              | theme         |
            | theme              | topic         |
            | topic              | theme         |
            | topic              | topic         |

    Scenario Outline: Other page types can be tagged with multiple topics
        Given a CMS user logs into the admin site
        And two topics exist
        When the CMS user tries to create a new <page type> page
        Then the user can link the page to both topics in the taxonomy editor tab

        Examples:
            | page type   |
            | information |
