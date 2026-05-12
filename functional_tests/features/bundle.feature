Feature: CMS users can manage bundles

    Background:
        Given a CMS user logs into the admin site

    # General bundle page scenarios
    Scenario: A content editor can see the date placeholder on the bundle page
        When the user navigates to the bundle creation page
        Then the date placeholder "YYYY-MM-DD HH:MM" is displayed in the "Publication date" textbox
    
    # Release calendar specific scenarios
    Scenario: A content editor can see the locale column when selecting a release calendar
        When the user navigates to the bundle creation page
        And the user opens the release calendar page chooser
        Then the locale column is displayed in the chooser

    Scenario Outline: A content editor can see the release calendar page title, status and release date when it has been selected under scheduling
        Given a release calendar page with a "<Release Status>" status and future release date exists
        When the user navigates to the bundle creation page
        And the user enters a bundle title
        And the user opens the release calendar page chooser
        And the user selects the existing release calendar page
        And the user saves the bundle as draft
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
        And  the user saves the bundle as draft
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
        And  the user saves the bundle as draft
        And  the user tries to set the release calendar page status to "Cancelled"
        Then the user sees a validation error preventing the cancellation because the page is in a bundle
    
    # Datasets specific scenarios
    Scenario: A content editor can select multiple datasets on the bundle page
        When the user navigates to the bundle creation page
        And the user selects multiple datasets
        Then the selected datasets are displayed in the "Data API datasets" section
    
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

    # Bundle E2E scenarios
    Scenario: A CMS user can create a draft bundle with approved information pages and preview teams
        Given the following approved information pages exist:
            | Title          |
            | Cookies        |
            | Privacy policy |
        And the following preview teams exist:
            | Team name      |
            | Help page team |
            | Privacy team   |
        When the user navigates to the bundle creation page
        And the user sets the bundle title as "Bundle help pages"
        And the user adds the following information pages to the bundle:
            | Title          |
            | Cookies        |
            | Privacy policy |
        And the user adds the following preview teams to the bundle:
            | Team name      |
            | Help page team |
            | Privacy team   |
        And the user saves the bundle as draft
        Then the bundle inspect page displays the following metadata:
            | Metadata Field                   | Metadata Value               |
            | Name                             | Bundle help pages            |
            | Created at                       |                              |
            | Created by                       |                              |
            | Status                           | Draft                        |
            | Approval status                  | Pending approval             |
            | Scheduled publication            | No scheduled publication     |
            | Associated release calendar page | N/A                          |
            | Teams                            | Help page team, Privacy team |
        And the bundle inspect page displays the following information pages:
            | Title          | Type             | Status           |
            | Cookies        | Information page | Ready to publish |
            | Privacy policy | Information page | Ready to publish |
        And the bundle inspect page shows no datasets

    Scenario: A CMS user can submit a draft bundle for review
        Given a bundle called "Bundle help pages release two" exists in "draft" with the following approved information pages:
            | Title                   |
            | Terms and conditions    |
            | Accessibility statement |
        When the user navigates to the bundle page in draft
        And the user submits the bundle to "review"
        Then the bundle inspect page displays the following metadata:
            | Metadata Field                   | Metadata Value                |
            | Name                             | Bundle help pages release two |
            | Created at                       |                               |
            | Created by                       |                               |
            | Status                           | In Preview                    |
            | Approval status                  | Pending approval              |
            | Scheduled publication            | No scheduled publication      |
            | Associated release calendar page | N/A                           |
            | Teams                            |                               |
        And the bundle inspect page displays the following information pages:
            | Title                   | Type             | Status           |
            | Terms and conditions    | Information page | Ready to publish |
            | Accessibility statement | Information page | Ready to publish |

    Scenario: A CMS user can approve a bundle in review to ready to publish
        Given a bundle called "Bundle help pages release three" exists in "review" with the following approved information pages:
            | Title           |
            | Browsers        |
            | Fair use policy |
        When the user navigates to the bundle page in review
        And the user submits the bundle to "ready to publish"
        Then the bundle inspect page displays the following metadata:
            | Metadata Field                   | Metadata Value                  |
            | Name                             | Bundle help pages release three |
            | Created at                       |                                 |
            | Created by                       |                                 |
            | Status                           | Ready to publish                |
            | Approval status                  |                                 |
            | Scheduled publication            | No scheduled publication        |
            | Associated release calendar page | N/A                             |
            | Teams                            |                                 |
        And the bundle inspect page displays the following information pages:
            | Title           | Type             | Status           |
            | Browsers        | Information page | Ready to publish |
            | Fair use policy | Information page | Ready to publish |
        And the bundle edit page is in read only mode

    Scenario: A CMS user can manually publish a ready to publish bundle
        Given a bundle called "Bundle help pages release four" exists in "ready to publish" with the following approved information pages:
            | Title          |
            | Contact us     |
            | Legal notice   |
        When the user navigates to the bundle page in ready to publish
        And the user publishes the bundle
        Then the user is taken back to the bundles listing page
        When the user filters the bundles listing page by "Published" status
        And the user clicks on the published bundle "Bundle help pages release four"
        Then the bundle inspect page displays the following metadata:
            | Metadata Field                   | Metadata Value                  |
            | Name                             | Bundle help pages release four  |
            | Created at                       |                                 |
            | Created by                       |                                 |
            | Status                           | Published                       |
            | Approval status                  |                                 |
            | Scheduled publication            | No scheduled publication        |
            | Associated release calendar page | N/A                             |
            | Teams                            |                                 |
        And the bundle inspect page displays the following information pages:
            | Title          | Type             | Status           |
            | Contact us     | Information page | Published        |
            | Legal notice   | Information page | Published        |
