Feature: CMS users can manage bundles

    Background:
        Given a CMS user logs into the admin site

    # General bundle page scenarios
    Scenario: A content editor can see the date placeholder on the bundle page
        When the user navigates to the bundle creation page
        Then the date placeholder "YYYY-MM-DD HH:MM" is displayed in the "Publication date" textbox
    
    # Release calendar specific scenarios
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
    
    # Datasets specific scenarios
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
    @smoke
    Scenario: A CMS user can create a draft bundle with approved information pages and preview teams
        Given the following approved information pages exist:
            | Title          |
            | Cookies        |
            | Privacy policy |
        And the following preview teams exist:
            | Team name        |
            | Help page team   |
            | Privacy team     |
        When the user navigates to the bundle creation page
        And the user sets the bundle title as "Bundle help pages"
        And the user adds the following information pages to the bundle:
            | Title          |
            | Cookies        |
            | Privacy policy |
        And the user adds the following preview teams to the bundle:
            | Team name        |
            | Help page team   |
            | Privacy team     |
        And the user saves the bundle as draft
        Then the bundle inspect page displays the following metadata:
            | Metadata Field                   | Metadata Value                                |
            | Name                             | Bundle help pages                             |
            | Created at                       |                                               |
            | Created by                       |                                               |
            | Status                           | Draft                                         |
            | Approval status                  | Pending approval                              |
            | Scheduled publication            | No scheduled publication                      |
            | Associated release calendar page | N/A                                           |
            | Teams                            | Help page team, Privacy team |
        And the bundle inspect page displays the following information pages:
            | Title          | Type             | Status |
            | Cookies        | Information page | Ready to publish |
            | Privacy policy | Information page | Ready to publish |
        And the bundle inspect page shows no datasets

    # Scenario: A CMS user can move a draft bundle to preview
    #     Given a draft bundle exists with the following approved information pages:
    #         | Title          |
    #         | Cookies        |
    #         | Privacy policy |
    #     When the user moves the bundle to preview
    #     Then the bundle inspect page displays the following metadata:
    #         | Metadata Field                   | Metadata Value                                 |
    #         | Name                             | Bundle help pages                              |
    #         | Status                           | In Preview                                     |
    #         | Approval status                  | Pending approval                               |
    #         | Scheduled publication            | No scheduled publication                       |
    #         | Associated release calendar page | N/A                                            |
    #         | Teams                            | Publishing team, Help page team, Privacy team |
    #     And the bundle inspect page displays the following information pages:
    #         | Title          | Type             | Status |
    #         | Cookies        | Information page | Draft  |
    #         | Privacy policy | Information page | Draft  |
    #     And the bundle inspect page shows no datasets


    # Scenario: A CMS user can create, add bundle contents and manually publish the bundle
    #     Given the user navigates to the Wagtail admin page
    #     When the user clicks on the bundles navigation item on the sidebar
    #     Then the user is on the bundles listing page
    #     When the user clicks on the "Add bundle" button
    #     Then the user is on the bundle creation page
    #     When the user enters a title for the bundle
    #     # The pages I am going to add here have been through the page workflow and have been approved
    #     And the user populates the bundles pages section with some pages
    #     And the user populates the bundles preview team section with some preview teams
    #     Then the user clicks on the "Save as draft" button
    #     Then the user clicks on the "Save to preview" button
    #     Then the user is on the bundle inspect page
    #     Then the user can see the following meta data <meta data goes here, maybe make it into a table idk> on the inspect page
    #     And the user can see the following pages in the bundle <pages go here, maybe make it into a table idk> on the inspect page
    #     And the user see "No datasets in bundle" in the inspect page since no datasets were added to the bundle
    #     And when the user clicks on the "Edit" button to go back to the bundle creation page
    #     And then the user clicks on the approve button
    #     Then the user is on the bundle inspect page
    #     And when the user clicks on the "Edit" button to go back to the bundle creation page
    #     Then the bundle creation page is now in read only mode
    #     And the user now clicks on the "Publish" button
    #     Then the bundle is published
    #     And the user can see a notification message confirming the bundle has been published
    #     And then the user filters for the publishes bundles in the bundles listing page
    #     Then the user can see the published bundle in the listing
    #     And the user clicks on the published bundle to go to the inspect page
    #     Then the user sees the bundle inspect page with the correct metadata, pages and datasets information

    # Scenario: A CMS user can create a bundle with a release calendar page, add contents and manually publish the bundle

    # Scenario: A CMS user can schedule a bundle using the publication date, add contents and the bundle is automatically published

    # Scenario: A CMS user can see the inspect for a published bundle
