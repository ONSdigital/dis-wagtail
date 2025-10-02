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
        And the user enters a title
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
        And the user enters a title
        And the user opens the release calendar page chooser
        Then the user cannot select the existing release calendar page

    Scenario Outline: A content editor updates the release calendar page details, after it has been assigned to a bundle and the change is reflected on the bundle edit page
        When the user manually creates a future release calendar page with a "Provisional" status
        And the user clicks the "Save Draft" button
        And the user navigates to the bundle creation page
        And the user enters a title
        And the user opens the release calendar page chooser
        And the user selects the existing release calendar page
        And the user clicks "Save as draft"
        And the user updates the selected release calendar page's title, release date and sets the status to "<New Status>"
        And returns to the bundle edit page
        Then the user sees the updated release calendar page's title, release date and the status "<New Status>"

    Examples:
      | New Status  |
      | Provisional |
      | Confirmed   |
      # A Cancelled release calendar page should not be added to bundle
      | Cancelled   |
