Feature: Users can create localised content in the CMS
    Background:
        Given a Publishing Officer logs into the admin site

    Scenario: The user is able to create a translated version of a page
        Given a published information page exists
        When the user edits the welsh information page
        And  the user converts the alias into an ordinary page
        And  the user adds Welsh content to the information page
        And  the welsh information page goes through the publishing steps with Publishing Officer as user and Publishing Admin as reviewer
        And  the user clicks "View Live" on the publish confirmation banner
        Then the published information page is displayed with Welsh content
        And the page furniture is displayed in Welsh

    Scenario: The user is able to switch between different language versions of a page
        Given a published information page exists
        And  a published information page translation exists
        When the user views the welsh information page
        Then the published information page is displayed with Welsh content
        And the user switches the page language to English
        Then the published information page is displayed with English content
        And the user switches the page language to Welsh
        Then the published information page is displayed with Welsh content

    Scenario: The user sees English content and Welsh page furniture when viewing a non-translated page
        Given a published information page exists
        When the user views the information page
        Then the published information page is displayed with English content
        And  the user switches the page language to Welsh
        Then the published information page is displayed with English content and Welsh livery
        And  the page furniture is displayed in Welsh

    Scenario: The user sees a message explaining the content is not translated when viewing a non-translated page
        Given a published information page exists
        When the user views the information page
        And  the user switches the page language to Welsh
        Then a message is displayed explaining that the content is not translated

    Scenario: The user is warned when editing an English version of a page with existing translations
        Given a published information page exists
        And  a published information page translation exists
        When the user edits the information page
        And  the user updates the content of the information page
        And  the information page goes through the publishing steps with Publishing Officer as user and Publishing Admin as reviewer
        Then a warning is displayed explaining that the page has existing translations

    Scenario: The user doesn't change the translation when editing the English page
        Given a published information page exists
        When the user edits the welsh information page
        And  the user converts the alias into an ordinary page
        And  the user adds Welsh content to the information page
        And  the welsh information page goes through the publishing steps with Publishing Officer as user and Publishing Admin as reviewer
        When the user edits the welsh information page
        And  the user switches to the English locale
        And  the user updates the content of the information page
        And  the information page goes through the publishing steps with Publishing Officer as user and Publishing Admin as reviewer
        And  the user views the welsh information page
        Then the published information page is displayed with Welsh content

    Scenario: The user doesn't change the English page when editing the translation
        Given a published information page exists
        When the user edits the information page
        And  the user switches to the Welsh locale
        And  the user converts the alias into an ordinary page
        And  the user adds Welsh content to the information page
        And  the welsh information page goes through the publishing steps with Publishing Officer as user and Publishing Admin as reviewer
        And  the user clicks "View Live" on the publish confirmation banner
        And  the user switches the page language to English
        Then the published information page is displayed with English content
