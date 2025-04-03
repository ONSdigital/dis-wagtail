Feature: CMS users can log in to the CMS site

    Scenario: A content editor can login to the admin site
        Given the user is a CMS admin
        When the user opens the beta CMS admin page
        And they enter a their valid username and password and click login
        Then they are taken to the CMS admin homepage
