Feature: Statistical Article Page components

    Background:
        Given a superuser logs into the admin site

    Scenario: A CMS user can create and publish a Statistical Article Page
        When the user goes to add a new statistical article page
        And the user adds basic statistical article page content
        And the user clicks "Publish"
        And the user clicks "View Live" on the publish confirmation banner
        Then the published statistical article page is displayed with the populated data


    Scenario: A CMS user can add a table on a Statistical Article Page
        When the user goes to add a new statistical article page
        And the user adds basic statistical article page content
        And the user adds a table with pasted content
        And the user clicks "Publish"
        And the user clicks "View Live" on the publish confirmation banner
        Then the published statistical article page is displayed with the populated data
        And the published statistical article page has the added table
        And the user can expand the footnotes

    Scenario: A CMS user can add a correction to a Statistical Article Page
        When the user goes to add a new statistical article page
        And the user adds basic statistical article page content
        And the user clicks "Publish"
        And the user returns to editing the statistical article page
        And the user adds a correction
        And the user clicks "Publish"
        And the user clicks "View Live" on the publish confirmation banner
        Then the published statistical article page has the added correction
        And the user can expand and collapse correction details

    Scenario: A CMS user can edit a correction to a Statistical Article Page
        When the user goes to add a new statistical article page
        And the user adds basic statistical article page content
        And the user clicks "Publish"
        And the user returns to editing the statistical article page
        And the user adds a correction
        And the user clicks "Publish"
        And the user returns to editing the statistical article page
        Then the user can edit the correction

    Scenario: A CMS user cannot delete a correction to a Statistical Article Page once it is published
        When the user goes to add a new statistical article page
        And the user adds basic statistical article page content
        And the user clicks "Publish"
        And the user returns to editing the statistical article page
        And the user adds a correction
        And the user clicks "Publish"
        And the user returns to editing the statistical article page
        Then the user cannot delete the correction

    Scenario: Corrections are saved in chronological order
        When the user goes to add a new statistical article page
        And the user adds basic statistical article page content
        And the user clicks "Publish"
        And the user returns to editing the statistical article page
        And the user adds a correction
        And the user clicks "Publish"
        And the user returns to editing the statistical article page
        And the user adds another correction using the add button at the bottom
        And the user clicks "Publish"
        And the user clicks "View Live" on the publish confirmation banner
        Then the published statistical article page has corrections in chronological order

    Scenario: A CMS user can view a superseded Statistical Article Page
        When the user goes to add a new statistical article page
        And the user adds basic statistical article page content
        And the user clicks "Publish"
        And the user returns to editing the statistical article page
        And the user updates the statistical article page content
        And the user adds a correction
        And the user clicks "Publish"
        And the user clicks "View Live" on the publish confirmation banner
        And the user clicks on "View superseded version"
        Then the user can view the superseded statistical article page

    Scenario: A CMS user can add a notice to a Statistical Article Page
        When the user goes to add a new statistical article page
        And the user adds basic statistical article page content
        And the user adds a notice
        And the user clicks "Publish"
        And the user clicks "View Live" on the publish confirmation banner
        Then the published statistical article page has the added notice
        And the user can expand and collapse notice details

    Scenario: A CMS user can add a correction and a notice to a Statistical Article Page
        When the user goes to add a new statistical article page
        And the user adds basic statistical article page content
        And the user clicks "Publish"
        And the user returns to editing the statistical article page
        And the user adds a correction
        And the user adds a notice
        And the user clicks "Publish"
        And the user clicks "View Live" on the publish confirmation banner
        Then the published statistical article page has the corrections and notices block
        And the user can click on "Show detail" to expand the corrections and notices block
        And the user can click on "Hide detail" to collapse the corrections and notices block

    Scenario: A CMS user can add headline figures to a Statistical Article Page
        When the user goes to add a new statistical article page
        And the user adds basic statistical article page content
        And the user adds headline figures
        And the user clicks "Publish"
        And the user clicks "View Live" on the publish confirmation banner
        Then the published statistical article page has the added headline figures

    Scenario: A CMS user can see date placeholders on a Statistical Article Page by textbox
        When the user goes to add a new statistical article page
        Then the date placeholder "YYYY-MM-DD" is displayed in the "Release date*" textbox
        And the date placeholder "YYYY-MM-DD" is displayed in the "Next release date" textbox

    Scenario: The related data page is linked and accessible when there are datasets related to a statistical article
        When the user goes to add a new statistical article page
        And the user adds basic statistical article page content
        And the user navigates to the related data editor tab
        And looks up and selects a dataset
        And manually enters a dataset link
        And the user clicks "Publish"
        And the user clicks "View Live" on the publish confirmation banner
        And the user clicks "View data used in this article" on the article page
        Then the related data page for the article is shown

    Scenario: The related data page is linked and accessible when there are datasets related to a statistical article in an internal environment
        Given the user is in an internal environment
        When the user goes to add a new statistical article page
        And the user adds basic statistical article page content
        And the user navigates to the related data editor tab
        And looks up and selects a dataset
        And manually enters a dataset link
        And the user clicks "Publish"
        And the user clicks "View Live" on the publish confirmation banner
        And the user clicks "View data used in this article" on the article page
        Then the related data page for the article is shown

    Scenario: When selecting related data for a statistical article the user sees unpublished datasets as default
        When the user goes to add a new statistical article page
        And the user adds basic statistical article page content
        And the user navigates to the related data editor tab
        And the user opens the dataset chooser
        Then unpublished datasets are shown by default in the dataset chooser

    Scenario: The dataset chooser shows published datasets when filter is set to published only
        When the user goes to add a new statistical article page
        And the user adds basic statistical article page content
        And the user navigates to the related data editor tab
        And the user opens the dataset chooser and sets the filter to published datasets
        Then only published datasets are shown in the dataset chooser

    Scenario: A CMS user can see a featured chart field on a Statistical Article Page
        When the user goes to add a new statistical article page
        And the user switches to the Promote tab
        Then the user sees a "Featured Chart" field

    Scenario: A CMS user can add a featured chart on a Statistical Article Page
        When the user goes to add a new statistical article page
        And the user adds basic statistical article page content
        And the user switches to the Promote tab
        And the user clicks "Line chart" in the featured chart streamfield block selector
        And the user fills in the line chart title
        And the user fills in the chart audio description
        And the user enters data into the chart table
        And the user clicks "Publish"
        Then submitting the Wagtail page edit form is successful

    Scenario: A CMS user can preview a featured chart on a Statistical Article Page
        Given a statistical article page with a configured featured chart exists
        But the statistical article page is not a featured article on its containing topic page
        When the user goes to edit the statistical article page
        And the user selects the "featured chart" preview mode
        Then the user sees a preview of the containing Topic page
        And the topic page preview contains the featured article component
        And the featured article component contains the featured chart

    Scenario: A featured chart preview is the version currently being edited
        Given a statistical article with valid streamfield content exists
        But the statistical article page is not a featured article on its containing topic page
        When the user goes to edit the statistical article page
        And the user switches to the Promote tab
        And the user clicks "Line chart" in the featured chart streamfield block selector
        And the user fills in the line chart title
        And the user fills in the chart audio description
        And the user enters data into the chart table
        And the user selects the "featured chart" preview mode
        Then the user sees a preview of the containing Topic page
        And the topic page preview contains the featured article component
        And the featured article component contains the featured chart

    Scenario: A featured chart is visible on the containing topic page
        Given a statistical article page with a configured featured chart exists
        And the statistical article page is selected as the featured article on its containing topic page
        When the user visits the containing topic page
        Then the user sees the published topic page
        And the featured article is shown
        And the featured article component contains the featured chart

    Scenario: A listing image is visible on the containing topic page
        Given a statistical article page with a configured listing image exists
        And the statistical article page is selected as the featured article on its containing topic page
        When the user visits the containing topic page
        Then the user sees the published topic page
        And the featured article is shown
        And the featured article component contains the featured article listing image

    Scenario: A CMS user can save a Statistical Article Page without a featured chart
        When the user goes to add a new statistical article page
        And the user adds basic statistical article page content
        And the user switches to the Promote tab
        And the user leaves the featured chart fields blank
        And the user clicks "Publish"
        Then submitting the Wagtail page edit form is successful

    Scenario: A CMS user can add an accordion section to a Statistical Article Page
        When the user goes to add a new statistical article page
        And the user adds basic statistical article page content
        And the user adds an accordion section with title and content
        And the user clicks "Publish"
        And the user clicks "View Live" on the publish confirmation banner
        Then the published statistical article page has the added accordion section
        And the user can expand and collapse the accordion section

    @no_javascript
    Scenario: The fallback equation is visible to non-JS users
        Given a statistical article page with equations exists
        Then the user can see the equation fallback

    Scenario: The fallback equation is not visible to non-JS users
        Given a statistical article page with equations exists
        Then the user cannot see the equation fallback

    Scenario: A chart on a statistical article page has a CSV download link
        When the user goes to add a new statistical article page
        And the user adds basic statistical article page content
        And the user adds a chart to the content
        And the user enters data into the chart table
        And the user clicks "Publish"
        And the user clicks "View Live" on the publish confirmation banner
        Then the page has a CSV download link for the chart
