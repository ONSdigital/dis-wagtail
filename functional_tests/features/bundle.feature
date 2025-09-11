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
        Given a Release Calendar with a release date in the future exists
        When the user goes to the bundle creation page
        And the user adds a title to the bundle
        And the user selects a release calendar page through the chooser
        And the user saves the bundle
        Then the user sees the release calendar page title, status and release date
@smoke
    Scenario: A content editor updates the release calendar status, after it has been assigned to a bundle and the change is reflected on the bundle edit page
        Given a Release Calendar with a release date in the future exists
        When the user goes to the bundle creation page
        And the user adds a title to the bundle
        And the user selects a release calendar page through the chooser
        And the user saves the bundle
        And the user sees the release calendar page title, status and release date
        Then the user changes the status of the release calendar page, after it has been selected
        And returns to the bundle with this release calendar page assigned
        And the user sees the release calendar page with the updated status
 