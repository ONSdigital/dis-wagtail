Feature: A general use of Methodology Page

    Scenario: A CMS user can create a Methodology Page
        Given a topic page exists under the homepage
        And  a Publishing Officer logs into the admin site
        When the user creates a methodology page as a child of the existing topic page
        And  the user populates the methodology page
        Then the user can create the page
        When the user opens the preview in a new tab
        Then the published methodology page is displayed with the populated data

    Scenario: A CMS user can add a published statistical articles in the Related publication section of the Methodology page
        Given a topic page exists under the homepage
        And  the user has created a statistical article in a series
        And  a superuser logs into the admin site
        When the user creates a methodology page as a child of the existing topic page
        And  the user populates the methodology page
        And  the user selects the article page in the Related publications block
        And  the user opens the preview in a new tab
        Then the article is displayed correctly under the Related publication section

    Scenario: A CMS user can add a Contact Details snippet on the Methodology page
        Given a topic page exists under the homepage
        And  a contact details snippet exists
        And  a superuser logs into the admin site
        When the user creates a methodology page as a child of the existing topic page
        And  the user populates the methodology page
        And  the user selects the Contact Details
        And  the user opens the preview in a new tab
        Then the Contact Details are visible on the page

    Scenario: The mandatory fields raise validation errors when left empty on the Methodology page.
        Given a topic page exists under the homepage
        And a superuser logs into the admin site
        When the user creates a methodology page as a child of the existing topic page
        And the user clicks the "Save draft" button
        Then the methodology page mandatory fields raise validation errors

    Scenario: The Last revised date field has appropriate validation on Methodology page.
        Given a topic page exists under the homepage
        And a superuser logs into the admin site
        When the user creates a methodology page as a child of the existing topic page
        And the user populates the methodology page
        And the Last revised date is set to be before the Publication date
        And the user clicks the "Save draft" button
        Then a validation error for the Last revised date is displayed

    Scenario: A CMS user can create and preview the Methodology page
        Given a topic page exists under the homepage
        And a superuser logs into the admin site
        When the user creates a methodology page as a child of the existing topic page
        And the user populates the methodology page
        Then the preview of the methodology page is displayed with the populated data

    Scenario: A CMS user can save and access a draft of the Methodology page
        Given a topic page exists under the homepage
        And a superuser logs into the admin site
        And the user creates a methodology page as a child of the existing topic page
        And the user populates the methodology page
        When the user clicks the "Save draft" button
        And the user navigates to the page history menu
        Then the saved draft version is visible
        And the preview of the methodology page matches the populated data

    Scenario: A CMS user can see the date placeholder in the date field of the Methodology page
        Given a topic page exists under the homepage
        And a superuser logs into the admin site
        When the user creates a methodology page as a child of the existing topic page
        Then the date placeholder "YYYY-MM-DD" is displayed in the "Publication date" textbox
        And the date placeholder "YYYY-MM-DD" is displayed in the "Last revised date" textbox
