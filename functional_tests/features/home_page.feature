Feature: There is a default home page

    Scenario: External user can see the homepage
        When An external user navigates to the ONS beta site homepage
        Then they can see the beta homepage
        And  they cannot see the breadcrumbs
