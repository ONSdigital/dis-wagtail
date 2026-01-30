Feature: Topic page creation and configuration in the Wagtail admin

    Background:
        Given a superuser logs into the admin site

    # Topic Page Creation
    Scenario: A CMS user can create a topic page under the home page
        Given a topic exists
        When the user tries to create a new topic page
        And the user fills in the required topic page content
        And the user selects the taxonomy topic
        And the user clicks "Publish"
        Then the user sees the success message "Page 'Test Title' created and published"

    # Field Validation
    Scenario: Topic page requires a title
        Given a topic exists
        When the user tries to create a new topic page
        And the user fills in the topic page summary
        And the user selects the taxonomy topic
        And the user clicks "Publish"
        Then the user sees the validation error "This field is required"

    Scenario: Topic page requires a summary when publishing
        Given a topic exists
        When the user tries to create a new topic page
        And the user fills in the topic page title
        And the user selects the taxonomy topic
        And the user clicks "Publish"
        Then the user sees the validation error "This field is required" in the summary field

    Scenario: Topic page requires a taxonomy topic
        When the user tries to create a new topic page
        And the user fills in the required topic page content
        And the user clicks "Publish"
        Then the user sees the taxonomy validation error

    Scenario: Topic page allows zero headline figures
        Given a topic page exists under the homepage
        When the user edits the topic page
        And the user clicks "Publish"
        Then the user does not see headline figure validation errors

    # Drafting and Previewing
    Scenario: A CMS user can save a topic page as draft
        Given a topic exists
        When the user tries to create a new topic page
        And the user fills in the required topic page content
        And the user selects the taxonomy topic
        And the user clicks the "Save Draft" button
        Then the user sees the draft saved message
        And the user can continue editing the page

    Scenario: A CMS user can view page history after saving a draft
        Given a topic exists
        When the user tries to create a new topic page
        And the user fills in the required topic page content
        And the user selects the taxonomy topic
        And the user clicks the "Save Draft" button
        When the user navigates to the page history menu
        Then the saved draft version is visible

    Scenario: A CMS user can preview an existing topic page
        Given a topic page exists under the homepage
        When the user edits the topic page
        And the user clicks toggle preview
        Then the topic page preview displays the page title and summary

    # Edge Case Handling - Related Articles
    Scenario: External related article requires a title
        Given a topic page exists under the homepage
        When the user edits the topic page
        And the user adds an external related article without a title
        And the user clicks "Publish"
        Then the user sees the validation error "This field is required when providing an external URL"

    Scenario: Related article must have either internal page or external URL
        Given a topic page exists under the homepage
        When the user edits the topic page
        And the user adds an empty related article
        And the user clicks "Publish"
        Then the user sees the validation error "You must select an internal page or provide an external URL"

    # Edge Case Handling - Time Series
    Scenario: Time series URL must be a valid ONS domain
        Given a topic page exists under the homepage
        When the user edits the topic page
        And the user adds a time series link with an invalid URL
        And the user clicks "Publish"
        Then the user sees the time series URL validation error
