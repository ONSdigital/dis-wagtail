Feature: Example scenarios

    Scenario: External user can see the homepage
        When An external user navigates to the ONS beta site
        Then they can see the beta homepage

    Scenario: A content editor can login to the admin site
        Given the user is a CMS admin
        When the user navigates to the beta CMS admin page
        And they enter a their valid username and password and click login
        Then they are taken to the CMS admin homepage
