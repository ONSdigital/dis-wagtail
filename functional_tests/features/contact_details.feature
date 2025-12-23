Feature: CMS users can create contact details snippets

    Background:
        Given a superuser logs into the admin site

    Scenario: A user creates a contact details snippet
        When a user goes to the "Contact details" snippet listing page
        And the user clicks the "Add contact details" button
        And the user fills in the contact details form with valid data
        And the user submits the contact details form
        Then the user sees a success message indicating the contact details snippet was created

    Scenario: A user attempts to create a duplicate contact details snippet
        Given a contact detail for John Doe exists
        When a user goes to the "Contact details" snippet listing page
        And the user clicks the "Add contact details" button
        And the user fills in the contact details form with John Doe's details
        And the user submits the contact details form
        Then the user sees an error message indicating a duplicate contact details snippet cannot be created

    Scenario: A user edits an existing contact details snippet
        Given a contact detail for John Doe exists
        When a user goes to the "Contact details" snippet listing page
        And the user clicks the "Edit" button for John Doe's contact details
        And the user updates the phone number
        And the user submits the contact details form
        Then the user sees a success message indicating the contact details snippet was updated

    Scenario: A user edits an existing contact details snippet to create a duplicate
        Given a contact detail for John Doe exists
        And a contact detail for Jane Smith exists
        When a user goes to the "Contact details" snippet listing page
        And the user clicks the "Edit" button for Jane Smith's contact details
        And the user updates the name and email to match John Doe's details
        And the user submits the contact details form
        Then the user sees an error message indicating a duplicate contact details snippet cannot be created
