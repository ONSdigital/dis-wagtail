Feature: CMS users can draft, edit, and publish topic pages

    Background:
        Given a superuser logs into the admin site

    Scenario: A CMS user can feature an article series
        Given a topic page exists under the homepage
        And the topic page has a statistical article in a series
        When the user edits the topic page
        And the user clicks the "Choose Article Series page" button
        And the user selects the article series
        And publishes the page
        And the user visits the topic page
        Then the topic page with the example content is displayed
        And the user can see the topic page featured article

    Scenario: The featured series on a topic page displays the latest article
        Given a topic page exists under the homepage
        And the user has created a statistical article in a series
        And the user has featured the series
        When the user creates a new statistical article in the series
        And the user visits the topic page
        Then the user can see the newly created article in featured spot

    Scenario: The 'View all related articles' link appears on a topic page
        Given a topic page exists under the homepage
        And the user has created a statistical article in a series
        When the user visits the topic page
        Then the user sees the 'View all related articles' link

    Scenario: The 'View all related methodology' link appears on a topic page
        Given a topic page exists under the homepage
        And the topic page has a child methodology page
        When the user visits the topic page
        Then the user sees the 'View all related methodology' link

    Scenario: The translated version of the topic page uses the same taxonomy
        Given a topic page exists under the homepage
        And the topic page has a Welsh translation
        When the user edits the topic page
        And the user switches to the Welsh locale
        And the user converts the alias into an ordinary page
        And the user goes to the Taxonomy tab
        Then the user is informed that the selected topic is copied from the English version

    Scenario: A CMS user can choose headline figures when editing a topic
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

    Scenario: A CMS user can add datasets to a topic page
        Given a topic page exists under the homepage
        When the user edits the topic page
        And looks up and selects a dataset
        And the user clicks "Publish"
        And the user views the topic page
        Then the selected datasets are displayed on the page
        And the user sees the 'View all related data' link

    Scenario: A CMS user can add a time series section to a topic page
        Given a topic page exists under the homepage
        When the user edits the topic page
        And the user adds a time series page link
        And the user clicks "Publish"
        And the user views the topic page
        Then the time series section is displayed on the page
        And the user sees the 'View all related time series' link
        And the time series item appears in the table of contents

    Scenario: Topic page highlighted articles show tagged articles from other topic pages when there are no descendants
        Given the following topic pages exist:
            | title        | topic     |
            | Topic Page A | Economy   |
            | Topic Page B | Inflation |
            | Topic Page C | CPI       |
        And "Topic Page B" has the following "articles":
            | series           | article   | release_date | topic   |
            | Article Series 1 | Article 1 | 2025-01-01   | Economy |
            | Article Series 2 | Article 2 | 2025-01-02   | Economy |
        And "Topic Page C" has the following "articles":
            | series           | article   | release_date | topic   |
            | Article Series 3 | Article 3 | 2025-01-04   | Economy |
        When the user visits "Topic Page A"
        Then the highlighted "articles" section is visible
        And the highlighted "articles" are displayed in this order:
            | article_name                |
            | Article Series 3: Article 3 |
            | Article Series 2: Article 2 |
            | Article Series 1: Article 1 |

    Scenario: Manually selected article appear first, followed by tagged articles sorted by latest release date
        Given the following topic pages exist:
            | title        | topic     |
            | Topic Page A | Economy   |
            | Topic Page B | Inflation |
            | Topic Page C | CPI       |
        And "Topic Page A" has the following "articles":
            | series                | article          | release_date | topic   |
            | Article Series Manual | Manual Article 1 | 2024-12-01   | Housing |
        And "Topic Page B" has the following "articles":
            | series           | article                  | release_date | topic   |
            | Article Series 1 | Article 1 Older Edition  | 2025-01-01   | Economy |
            | Article Series 1 | Article 2 Latest Edition | 2025-01-02   | Economy |
            | Article Series 2 | Article 3                | 2025-01-03   | Economy |
        And "Topic Page C" has the following "articles":
            | series           | article   | release_date | topic   |
            | Article Series 3 | Article 4 | 2025-01-04   | Economy |
        When the user edits "Topic Page A"
        And the user manually adds "Manual Article 1" in the highlighted "articles" section
        And the user clicks "Publish"
        And the user visits "Topic Page A"
        Then the highlighted "articles" section is visible
        And the highlighted "articles" are displayed in this order:
            | article_name                            |
            | Article Series Manual: Manual Article 1 |
            | Article Series 3: Article 4             |
            | Article Series 2: Article 3             |

    Scenario: Highlighted articles show a mix of descendant, manually selected, and tagged articles
        Given the following topic pages exist:
            | title        | topic     |
            | Topic Page A | Economy   |
            | Topic Page B | Inflation |
            | Topic Page C | CPI       |
        And "Topic Page A" has the following "articles":
            | series   | article              | release_date | topic          |
            | Series 1 | Descendant Article 1 | 2025-01-02   | Housing        |
            | Series 2 | Descendant Article 2 | 2025-01-03   | Prices         |
            | Series 3 | Descendant Article 3 | 2025-01-04   | Sustainability |
        And "Topic Page B" has the following "articles":
            | series   | article          | release_date | topic   |
            | B Series | Tagged Article B | 2025-01-01   | Economy |
        And "Topic Page C" has the following "articles":
            | series   | article          | release_date | topic   |
            | C Series | Tagged Article C | 2025-01-05   | Economy |
        When the user edits "Topic Page A"
        And the user manually adds "Descendant Article 1" in the highlighted "articles" section
        And the user clicks "Publish"
        And the user visits "Topic Page A"
        Then the highlighted "articles" section is visible
        And the highlighted "articles" are displayed in this order:
            | article_name                   |
            | Series 1: Descendant Article 1 |
            | C Series: Tagged Article C     |
            | Series 3: Descendant Article 3 |

    Scenario: Topic page highlighted methodologies show tagged methodologies from other topic pages when there are no descendants
        Given the following topic pages exist:
            | title        | topic     |
            | Topic Page A | Economy   |
            | Topic Page B | Inflation |
            | Topic Page C | CPI       |
        And "Topic Page B" has the following "methodologies":
            | title              | publication_date | topic   |
            | Methodology Page 1 | 2025-01-01       | Economy |
            | Methodology Page 2 | 2025-01-02       | Economy |
        And "Topic Page C" has the following "methodologies":
            | title              | publication_date | topic   |
            | Methodology Page 3 | 2025-01-04       | Economy |
        When the user visits "Topic Page A"
        Then the highlighted "methodologies" section is visible
        And the highlighted "methodologies" are displayed in this order:
            | methodology_name   |
            | Methodology Page 3 |
            | Methodology Page 2 |
            | Methodology Page 1 |

    Scenario: Manually selected methodologies appear first, followed by tagged methodologies sorted by publication date
        Given the following topic pages exist:
            | title        | topic     |
            | Topic Page A | Economy   |
            | Topic Page B | Inflation |
            | Topic Page C | CPI       |
        And "Topic Page A" has the following "methodologies":
            | title                | publication_date | topic   |
            | Manual Methodology 1 | 2024-12-01       | Housing |
        And "Topic Page B" has the following "methodologies":
            | title              | publication_date | topic   |
            | Methodology Page 1 | 2025-01-01       | Economy |
            | Methodology Page 2 | 2025-01-02       | Economy |
            | Methodology Page 3 | 2025-01-03       | Economy |
        And "Topic Page C" has the following "methodologies":
            | title              | publication_date | topic   |
            | Methodology Page 4 | 2025-01-04       | Economy |
        When the user edits "Topic Page A"
        And the user manually adds "Manual Methodology 1" in the highlighted "methodologies" section
        And the user clicks "Publish"
        And the user visits "Topic Page A"
        Then the highlighted "methodologies" section is visible
        And the highlighted "methodologies" are displayed in this order:
            | methodology_name     |
            | Manual Methodology 1 |
            | Methodology Page 4   |
            | Methodology Page 3   |

    Scenario: Highlighted methodologies show a mix of descendant, manually selected, and tagged methodologies
        Given the following topic pages exist:
            | title        | topic     |
            | Topic Page A | Economy   |
            | Topic Page B | Inflation |
            | Topic Page C | CPI       |
        And "Topic Page A" has the following "methodologies":
            | title                         | publication_date | topic          |
            | Descendant Methodology Page 1 | 2025-01-02       | Housing        |
            | Descendant Methodology Page 2 | 2025-01-03       | Prices         |
            | Descendant Methodology Page 3 | 2025-01-04       | Sustainability |
        And "Topic Page B" has the following "methodologies":
            | title                     | publication_date | topic   |
            | Tagged Methodology Page B | 2025-01-01       | Economy |
        And "Topic Page C" has the following "methodologies":
            | title                     | publication_date | topic   |
            | Tagged Methodology Page C | 2025-01-05       | Economy |
        When the user edits "Topic Page A"
        And the user manually adds "Descendant Methodology Page 1" in the highlighted "methodologies" section
        And the user clicks "Publish"
        And the user visits "Topic Page A"
        Then the highlighted "methodologies" section is visible
        And the highlighted "methodologies" are displayed in this order:
            | methodology_name              |
            | Descendant Methodology Page 1 |
            | Tagged Methodology Page C     |
            | Descendant Methodology Page 3 |
