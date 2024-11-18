Feature: Example scenarios

    Scenario: External user can see the homepage
        When An external user navigates to the ONS beta site
        Then they can see the beta homepage

    Scenario: A content editor can login to the admin site
        Given the user is a CMS admin
        When the user navigates to the beta CMS admin page
        And they enter a their valid username and password and click login
        Then they are taken to the CMS admin homepage

    Scenario: A content editor can create an example page
        Given the user is a CMS admin
        And the user logs into the CMS admin site
        When the user navigates to the home page and clicks create new page
        And they enter some example page information
        And they click Publish
        Then the new Example page is visible on the website
