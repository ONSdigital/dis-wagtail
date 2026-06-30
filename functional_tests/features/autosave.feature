@autosave_enabled
Feature: Wagtail Autosave
    As a wagtail cms editor
    I want my content to be automatically saved
    So that I don't lose my work

    Background:
        Given a published index page exists
        And a Publishing Officer logs into the admin site

    Scenario: Content is saved when autosave is enabled
        Given an information page exists
        When the user edits the information page
        And the unsaved controller gets it's initial snapshot
        And the user types content into the information page title
        And the user types content into the information page summary
        And the user refreshes the page
        Then the typed content is preserved in the editor
