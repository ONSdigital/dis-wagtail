Feature: CMS users can manage bundles


    Background:
        Given a CMS user logs into the admin site

    Scenario: A content editor can see the locale column when selecting a release calendar
        When the user goes to the bundle creation page
        And the user opens the release calendar page chooser
        Then the locale column is displayed in the chooser

    Scenario: A content editor can see the locale column when selecting a page
        When the user goes to the bundle creation page
        And the user opens the release calendar page chooser
        Then the locale column is displayed in the chooser
    
    Scenario: A content editor can see the date placeholder on the bundle page
        When the user goes to the bundle creation page
        Then the date placeholder "YYYY-MM-DD HH:MM" is displayed in the "Publication date" textbox
