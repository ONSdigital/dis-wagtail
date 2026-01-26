Feature: Table of Contents components

    Background:
        Given a statistical article page with sections exists

    Scenario: User sees the table of contents on statistical article page
        When the user visits the statistical article page
        Then they should see the table of contents

    Scenario: User see the first item highlighted in the table of contents on statistical article page
        When the user visits the statistical article page
        Then they should see the first item highlighted in the table of contents

    Scenario: User sees item get highlighted in the table of contents on statistical article page when scrolling
        When the user visits the statistical article page
        And they scroll to the second section
        Then they should see the second item highlighted in the table of contents

    Scenario: User clicks on an item in the table of contents and it becomes highlighted
        When the user visits the statistical article page
        And they click on the second item in the table of contents
        Then they should see the second item highlighted in the table of contents

    Scenario: User clicks on an item then scrolls back up and the first item becomes highlighted
        When the user visits the statistical article page
        And they click on the second item in the table of contents
        And they scroll back to the top of the page
        Then they should see the first item highlighted in the table of contents
