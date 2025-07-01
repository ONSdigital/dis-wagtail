# Feature: Simple JWT Authentication Test
#     Test basic JWT cookie authentication flow

#     @smoke
#     @cognito_enabled
#     Scenario: Can access admin page with valid JWT tokens
#         Given I have valid JWT tokens
#         When I set the authentication cookies
#         And I navigate to the admin page
#         Then I should see the admin dashboard
#         And I should not see a login page

#     @cognito_enabled
#     Scenario: Cannot access admin without tokens
#         Given I do not have authentication cookies
#         When I navigate to the admin page
#         Then I should be redirected to login