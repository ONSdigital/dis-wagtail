Feature: A general use of Methodology Page

    Scenario: A CMS user can create and publish a Methodology Page
        Given a topic page exists under a theme page
        And a CMS user logs into the admin site
        When the user creates a methodology page as a child of the existing topic page
        And the user populates the methodology page
        And the user clicks "Publish page"
        And the user clicks "View Live" on the publish confirmation banner
        Then the published methodology page is displayed with the populated data
    
    Scenario: A CMS user can add a published statistical articles in the Related publication section of the Methodology page
        Given a topic page exists under a theme page
        And the user has created a statistical article in a series
        And a CMS user logs into the admin site
        When the user creates a methodology page as a child of the existing topic page
        And the user populates the methodology page
        And the user selects the article page in the Related publications block
        And the user clicks "Publish page"
        And the user clicks "View Live" on the publish confirmation banner
        Then the article is displayed correctly under the Related publication section

    Scenario: A CMS user can add a Contact Details snippet on the Methodology page
        Given a topic page exists under a theme page
        And a contact details snippet exists
        And a CMS user logs into the admin site
        When the user creates a methodology page as a child of the existing topic page
        And the user populates the methodology page
        And the user selects the Contact Details
        And the user clicks "Publish page"
        And the user clicks "View Live" on the publish confirmation banner
        Then the Contact Details are visible on the page

    Scenario: The mandatory fields raise validation errors when left empty on the Methodology page.
        Given a topic page exists under a theme page
        And a CMS user logs into the admin site
        When the user creates a methodology page as a child of the existing topic page
        And the user clicks the "Save Draft" button and waits for the page to reload
        Then the mandatory fields raise a validation error

    Scenario: The Last revised date field has appropriate validation on Methodology page.
        Given a topic page exists under a theme page
        And a CMS user logs into the admin site
        When the user creates a methodology page as a child of the existing topic page
        And the user populates the methodology page
        And the Last revised date is set to be before the Publication date
        And clicks the "Save Draft" button
        Then a validation error for the Last revised date is displayed

    Scenario: A CMS user can create and preview the Methodology page
        Given a topic page exists under a theme page
        And a CMS user logs into the admin site
        When the user creates a methodology page as a child of the existing topic page
        And the user populates the methodology page
        Then the preview is visible with the populated data
