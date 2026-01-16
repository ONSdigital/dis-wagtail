Feature: There is a default home page

    Scenario: External user can see the homepage
        When An external user navigates to the ONS beta site homepage
        Then they can see the beta homepage
        And  they cannot see the breadcrumbs

    Scenario: Wagtail Core Default Login Link is shown on the homepage
        When An external user navigates to the ONS beta site homepage
        And the user clicks on the Wagtail Core Default Login link
        Then they are redirected to the Wagtail admin login page
