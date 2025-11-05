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

    @bundle_api_enabled
    Scenario: A content editor can see selected datasets on the inspect page
        When the user goes to the bundle creation page
        And the user sets the bundle title
        And the user selects multiple datasets
        And the user saves the bundle as draft
        And the user clicks on the inspect link for the created bundle
        Then the selected datasets are displayed in the inspect view

    @bundle_api_enabled
    Scenario: A content editor can preview selected datasets on the inspect page
        When the user goes to the bundle creation page
        And the user sets the bundle title
        And the user selects multiple datasets
        And the user saves the bundle as draft
        And the user clicks on the inspect link for the created bundle
        And the user opens the preview for one of the selected datasets
        Then the user can see the preview items dropdown

    Scenario: A content editor can select multiple datasets on the bundle page when the user is in an internal environment
        Given the user is in an internal environment
        When the user goes to the bundle creation page
        And the user selects multiple datasets
        Then the selected datasets are displayed in the "Data API datasets" section

    Scenario: A CMS user cannot see the published state dropdown when selecting datasets for a bundle
        When the user goes to the bundle creation page
        And the user opens the bundle datasets chooser
        Then the published state filter is not displayed in the chooser
