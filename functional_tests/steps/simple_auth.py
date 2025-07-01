# # functional_tests/steps/simple_auth.py

# import uuid
# import json
# from behave import given, when, then
# from django.conf import settings
# from django.contrib.auth import get_user_model
# from django.contrib.auth.models import Group

# # Import after Django is initialized
# from cms.auth.tests.helpers import CognitoTokenMixin

# User = get_user_model()


# @given("I have valid JWT tokens")
# def create_valid_tokens(context):
#     """Create valid JWT tokens for testing."""
#     print("\n=== CREATING JWT TOKENS ===")

#     # Use the keypair from context (set by @cognito_enabled tag)
#     keypair = context.test_keypair
#     context.user_uuid = str(uuid.uuid4())

#     print(f"User UUID: {context.user_uuid}")
#     print(f"Keypair KID: {keypair.kid}")

#     # Create helper instance
#     helper = CognitoTokenMixin()
#     helper.keypair = keypair
#     helper.user_uuid = context.user_uuid

#     # Generate tokens with admin role
#     access_token, id_token = helper.generate_tokens(groups=["role-admin"])

#     print(f"Access Token (first 50 chars): {access_token[:50]}...")
#     print(f"ID Token (first 50 chars): {id_token[:50]}...")

#     # Store tokens in context
#     context.access_token = access_token
#     context.id_token = id_token

#     # Create the user in database (mimicking what the middleware would do)
#     # print("\n=== CREATING USER IN DATABASE ===")
#     # user, created = User.objects.get_or_create(
#     #     external_user_id=context.user_uuid,
#     #     defaults={
#     #         "email": f"{context.user_uuid}@example.com",
#     #         "username": f"{context.user_uuid}@example.com",
#     #         "first_name": "Test",
#     #         "last_name": "Admin",
#     #     },
#     # )

#     # if created:
#     #     user.set_unusable_password()
#     #     user.is_staff = True
#     #     user.is_superuser = True
#     #     user.save()
#     #     print(f"User already exists: {user.username}")

#     # # Assign groups
#     # print("\n=== ASSIGNING GROUPS ===")
#     # admin_group, _ = Group.objects.get_or_create(name=settings.PUBLISHING_ADMIN_GROUP_NAME)
#     # viewers_group, _ = Group.objects.get_or_create(name=settings.VIEWERS_GROUP_NAME)
#     # user.groups.add(admin_group, viewers_group)
#     # print(f"User groups: {list(user.groups.values_list('name', flat=True))}")

#     # context.test_user = user
#     # print(f"User is_staff: {user.is_staff}")
#     # print(f"User is_superuser: {user.is_superuser}")


# # @given("I do not have authentication cookies")
# # def no_auth_cookies(context):
# #     """Ensure no authentication cookies are set."""
# #     print("\n=== CLEARING COOKIES ===")
# #     context.page.context.clear_cookies()


# @when("I set the authentication cookies")
# def set_auth_cookies(context):
#     """Set JWT authentication cookies in the browser."""
#     print("\n=== SETTING COOKIES ===")

#     cookies = [
#         {
#             "name": settings.ACCESS_TOKEN_COOKIE_NAME,
#             "value": context.access_token,
#             "domain": "localhost",
#             "path": "/",
#             "httpOnly": True,
#             "secure": False,
#             "sameSite": "Lax",
#         },
#         {
#             "name": settings.ID_TOKEN_COOKIE_NAME,
#             "value": context.id_token,
#             "domain": "localhost",
#             "path": "/",
#             "httpOnly": True,
#             "secure": False,
#             "sameSite": "Lax",
#         },
#         {
#             "name": settings.CSRF_COOKIE_NAME,
#             "value": "test-csrf-token",
#             "domain": "localhost",
#             "path": "/",
#             "httpOnly": False,
#             "secure": False,
#             "sameSite": "Lax",
#         },
#     ]

#     for cookie in cookies:
#         print(f"Setting cookie: {cookie['name']} = {cookie['value'][:50]}...")

#     context.page.context.add_cookies(cookies)

#     # Verify cookies were set
#     browser_cookies = context.page.context.cookies()
#     print(f"\nBrowser has {len(browser_cookies)} cookies set")
#     for cookie in browser_cookies:
#         print(f"  - {cookie['name']}: {cookie['value'][:50]}...")


# @when("I navigate to the admin page")
# def navigate_to_admin(context):
#     """Navigate to the Wagtail admin page."""
#     context.page.goto(f"{context.base_url}")
#     admin_url = f"{context.base_url}{'/admin/'}"
#     print(f"\n=== NAVIGATING TO ADMIN ===")
#     print(f"URL: {admin_url}")

#     # Enable console logging to see any JavaScript errors
#     context.page.on("console", lambda msg: print(f"[CONSOLE] {msg.text}"))

#     # Enable request/response logging
#     context.page.on("request", lambda request: print(f"[REQUEST] {request.method} {request.url}"))
#     context.page.on("response", lambda response: print(f"[RESPONSE] {response.status} {response.url}"))

#     # Navigate and wait for either success or redirect
#     response = context.page.goto(admin_url, wait_until="networkidle")

#     print(f"\nResponse status: {response.status}")
#     print(f"Response URL: {response.url}")

#     # If we get a 500 error, try to get more info
#     if response.status == 500:
#         print("\n=== 500 ERROR - CHECKING PAGE CONTENT ===")
#         content = context.page.content()

#         # Look for Django debug info if DEBUG=True
#         if "django.views.debug" in content:
#             # Try to extract the error message
#             error_element = context.page.query_selector(".exception_value")
#             if error_element:
#                 print(f"Exception: {error_element.inner_text()}")

#             # Try to get traceback
#             traceback_element = context.page.query_selector("#traceback")
#             if traceback_element:
#                 print(f"Traceback preview: {traceback_element.inner_text()[:500]}...")
#         else:
#             # Just show first part of response
#             print(f"Page content (first 1000 chars): {content[:1000]}")

#     # Store response for assertions
#     context.last_response = response


# # @then("I should see the admin dashboard")
# # def verify_admin_dashboard(context):
# #     """Verify we can see the admin dashboard."""
# #     print("\n=== VERIFYING ADMIN DASHBOARD ===")

# #     # Check if we're on the admin page
# #     current_url = context.page.url
# #     print(f"Current URL: {current_url}")

# #     # Look for admin-specific elements
# #     admin_indicators = [
# #         ("body.ready", "body with ready class"),
# #         (".w-header", "Wagtail header"),
# #         ("#wagtail", "Wagtail container"),
# #         (".w-sidebar", "Wagtail sidebar"),
# #     ]

# #     found_indicators = []
# #     for selector, description in admin_indicators:
# #         element = context.page.query_selector(selector)
# #         if element:
# #             found_indicators.append(description)
# #             print(f"✓ Found: {description}")
# #         else:
# #             print(f"✗ Not found: {description}")

# #     # Check page title
# #     title = context.page.title()
# #     print(f"\nPage title: {title}")

# #     if not found_indicators:
# #         # Get page content for debugging
# #         content = context.page.content()
# #         print(f"\nPage content preview: {content[:500]}...")
# #         raise AssertionError("No admin dashboard indicators found")

# #     print(f"\nFound {len(found_indicators)} admin indicators")


# # @then("I should not see a login page")
# # def verify_not_login_page(context):
# #     """Verify we're not on the login page."""
# #     print("\n=== VERIFYING NOT LOGIN PAGE ===")

# #     current_url = context.page.url
# #     print(f"Current URL: {current_url}")

# #     # Check for login page indicators
# #     login_indicators = [
# #         ("form[action*='login']", "login form"),
# #         ("input[name='username']", "username field"),
# #         ("input[name='password']", "password field"),
# #         (".login", "login class"),
# #     ]

# #     found_login_elements = []
# #     for selector, description in login_indicators:
# #         element = context.page.query_selector(selector)
# #         if element:
# #             found_login_elements.append(description)
# #             print(f"✗ Found login element: {description}")

# #     if found_login_elements:
# #         raise AssertionError(f"Found login page elements: {', '.join(found_login_elements)}")

# #     if "/login" in current_url:
# #         raise AssertionError(f"URL contains /login: {current_url}")

# #     print("✓ Not on login page")


# # @then("I should be redirected to login")
# # def verify_redirected_to_login(context):
# #     """Verify we were redirected to the login page."""
# #     print("\n=== VERIFYING LOGIN REDIRECT ===")

# #     current_url = context.page.url
# #     print(f"Current URL: {current_url}")

# #     # Check if we're on a login page
# #     if "/login" not in current_url:
# #         # Check for login form elements
# #         login_form = context.page.query_selector("form[action*='login']")
# #         if not login_form:
# #             raise AssertionError(f"Not redirected to login. Current URL: {current_url}")

# #     print("✓ Successfully redirected to login")"Created new user: {user.username}")
# #     else:
# #         print(f
