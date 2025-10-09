Feature: An ONS website user can accept, reject, and manage cookies using the cookies banner and management page
    Background:
        Given the browsers cookies are cleared

    Scenario: All optional cookies are disabled by default
        When An external user navigates to the ONS beta site homepage
        Then all the optional cookies are disabled in the ons_cookie_policy cookie in the browser

    Scenario: An external website user accepts additional cookies in the cookies banner
        When An external user navigates to the ONS beta site homepage
        And the cookies banner is displayed
        And the user is clicks "Accept additional cookies" on the cookies banner
        Then all the optional cookies are enabled in the ons_cookie_policy cookie in the browser

    Scenario: An external website user rejects additional cookies in the cookies banner
        When An external user navigates to the ONS beta site homepage
        And the cookies banner is displayed
        And the user is clicks "Reject additional cookies" on the cookies banner
        Then all the optional cookies are disabled in the ons_cookie_policy cookie in the browser

    Scenario Outline: An external website user can manage cookies via the cookies management page
        When An external user navigates to the ONS beta site homepage
        And the cookies banner is displayed
        And the user clicks "View cookies" on the cookies banner
        And the user is taken to the cookies management page
        Then all the optional cookies are turned off by default
        When the user turns "<Usage>" the "usage" cookies
        And the user turns "<Campaigns>" the "campaigns" cookies
        And the user turns "<Settings>" the "settings" cookies
        And the user clicks "Save settings"
        Then a message confirming cookies settings have been saved is displayed
        And the cookies options still reflect the user's choices
        And only the chosen optional cookies are enabled in the ons_cookie_policy cookie in the browser
        And the "Return to previous page" link takes the user back to the homepage

        Examples:
            | Usage | Campaigns | Settings |
            | On    | Off       | Off      |
            | Off   | On        | Off      |
            | Off   | Off       | On       |
            | On    | On        | Off      |
            | On    | Off       | On       |
            | Off   | On        | On       |
            | Off   | Off       | Off      |
            | On    | On        | On       |
