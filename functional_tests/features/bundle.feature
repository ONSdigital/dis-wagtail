Feature: CMS users can manage bundles

    Background:
        Given a CMS user logs into the admin site

    Scenario: A content editor can see the locale column when selecting a release calendar
        When the user navigates to the bundle creation page
        And the user opens the release calendar page chooser
        Then the locale column is displayed in the chooser

    Scenario: A content editor can see the locale column when selecting a page
        When the user navigates to the bundle creation page
        And the user opens the release calendar page chooser
        Then the locale column is displayed in the chooser

    Scenario: A content editor can see the date placeholder on the bundle page
        When the user navigates to the bundle creation page
        Then the date placeholder "YYYY-MM-DD HH:MM" is displayed in the "Publication date" textbox

    Scenario: A content editor can select multiple datasets on the bundle page
        When the user navigates to the bundle creation page
        And the user selects multiple datasets
        Then the selected datasets are displayed in the "Data API datasets" section

    Scenario Outline: A content editor can see the release calendar page title, status and release date when it has been selected under scheduling
        Given a release calendar page with a "<Release Status>" status and future release date exists
        When the user navigates to the bundle creation page
        And the user enters a bundle title
        And the user opens the release calendar page chooser
        And the user selects the existing release calendar page
        And the user clicks "Save as draft"
        Then the user sees the release calendar page title, status and release date

    Examples:
      | Release Status |
      | Provisional    |
      | Confirmed      |

    Scenario: A content editor cannot add a "Cancelled" release calendar page to a bundle
        Given a release calendar page with a "Cancelled" status and future release date exists
        When the user navigates to the bundle creation page
        And the user enters a bundle title
        And the user opens the release calendar page chooser
        Then the user cannot see the "Cancelled" release calendar page

    Scenario Outline: A content editor updates the release calendar page details, after it has been assigned to a bundle and the change is reflected on the bundle edit page
        Given a release calendar page with a "Provisional" status and future release date exists
        When the user navigates to the bundle creation page
        And  the user enters a bundle title
        And  the user opens the release calendar page chooser
        And  the user selects the existing release calendar page
        And  the user clicks "Save as draft"
        And  the user updates the selected release calendar page's title, release date and sets the status to "<New Status>"
        And  returns to the bundle edit page
        Then the user sees the updated release calendar page's title, release date and the status "<New Status>"

    Examples:
      | New Status  |
      | Provisional |
      | Confirmed   |

    Scenario: A content editor cannot set a release calendar page to cancelled when it is in a bundle
        Given a release calendar page with a "Provisional" status and future release date exists
        When the user navigates to the bundle creation page
        And  the user enters a bundle title
        And  the user opens the release calendar page chooser
        And  the user selects the existing release calendar page
        And  the user clicks "Save as draft"
        And  the user tries to set the release calendar page status to "Cancelled"
        Then the user sees a validation error preventing the cancellation because the page is in a bundle

    @bundle_api_enabled
    Scenario: A content editor can see selected datasets on the inspect page
        When the user navigates to the bundle creation page
        And the user sets the bundle title
        And the user selects multiple datasets
        And the user saves the bundle as draft
        And the user clicks on the inspect link for the created bundle
        Then the selected datasets are displayed in the inspect view

    @bundle_api_enabled
    Scenario: A content editor can preview selected datasets on the inspect page
        When the user navigates to the bundle creation page
        And the user sets the bundle title
        And the user selects multiple datasets
        And the user saves the bundle as draft
        And the user clicks on the inspect link for the created bundle
        And the user opens the preview for one of the selected datasets
        Then the user can see the preview items dropdown

    Scenario: A content editor can select multiple datasets on the bundle page when the user is in an internal environment
        Given the user is in an internal environment
        When the user navigates to the bundle creation page
        And the user selects multiple datasets
        Then the selected datasets are displayed in the "Data API datasets" section

    Scenario: A CMS user cannot see the published state dropdown when selecting datasets for a bundle
        When the user navigates to the bundle creation page
        And the user opens the bundle datasets chooser
        Then the published state filter is not displayed in the chooser
