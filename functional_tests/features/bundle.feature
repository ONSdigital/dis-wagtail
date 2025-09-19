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

    Scenario: A content editor can select multiple datasets on the bundle page
        When the user goes to the bundle creation page
        And the user selects multiple datasets
        Then the selected datasets are displayed in the "Data API datasets" section
    
     Scenario: A content editor can see the release calendar page title, status and release date when a release calendar page has been selected under scheduling
        Given a release calendar page with a future release date exists
        When the user goes to the bundle creation page
        And the user creates a bundle with this release calendar page
        And the user saves the bundle
        Then the user sees the release calendar page title, status and release date

    Scenario: A content editor updates the release calendar details and sees the changes reflected on the bundle edit page
        Given a release calendar page with a future release date exists
        When the user goes to the bundle creation page
        And the user creates a bundle with this release calendar page
        And the user saves the bundle
        And the user updates the selected release calendar's title, status and release date
        And returns to the bundle edit page
        Then the user sees the updated release calendar page title, status and release date
