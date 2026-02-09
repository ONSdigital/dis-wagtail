Feature: There is a default home page

    Scenario: External user can see the homepage
        When An external user navigates to the ONS beta site homepage
        Then they can see the beta homepage
        And  they cannot see the breadcrumbs

    Scenario: Wagtail Core Default Login Link is shown on the homepage
        When An external user navigates to the ONS beta site homepage
        And the user clicks on the Wagtail Core Default Login link
        Then they are redirected to the Wagtail admin login page

    Scenario: User initiates a search from the homepage
        When An external user navigates to the ONS beta site homepage
        And they click the search toggle button
        And they enter "articles" in the search field
        And they submit the search form
        Then they should be redirected to the search page with query "articles"
