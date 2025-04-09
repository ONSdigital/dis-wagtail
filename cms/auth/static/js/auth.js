/* eslint-disable no-console */

import SessionManagement from 'dis-authorisation-client-js';

const logoutURL = `${window.location.origin}/${window.wagtailAdminHomePath}logout/`;
const extendSessionURL = `${window.location.origin}/${window.wagtailAdminHomePath}extend-session/`;

function getCookieByName(name) {
  console.debug('[WAGTAIL] Getting cookie by name:', name);
  const cookies = document.cookie;
  if (!cookies) {
    return null;
  }
  const cookie = cookies
    .split(';')
    .map((c) => c.trim())
    .map((c) => c.split('='))
    .find((pair) => pair[0] === name);
  return cookie ? cookie[1] : null;
}

function fetchWithCsrf(url, method = 'POST', body = null, headers = {}) {
  const csrfToken = getCookieByName(window.csrfCookieName);
  if (!csrfToken) {
    console.error('[WAGTAIL] CSRF token not found.');
    return null;
  }

  const defaultHeaders = {
    'Content-Type': 'application/json',
    [window.csrfHeaderName]: csrfToken,
  };

  try {
    return fetch(url, {
      method,
      headers: { ...defaultHeaders, ...headers },
      credentials: 'include',
      body: body ? JSON.stringify(body) : null,
    });
  } catch (error) {
    console.error(`[WAGTAIL] Error during ${method} request to ${url}:`, error);
    return null;
  }
}

function logout() {
  console.log('[WAGTAIL] Attempting logout...');
  fetchWithCsrf(logoutURL)
    .then((response) => {
      if (response?.ok) {
        const redirectURL = response.redirected ? response.url : window.location.origin;
        console.log('[WAGTAIL] Logout successful. Redirecting to:', redirectURL);
        window.location.href = redirectURL;
        return;
      }

      console.error('[WAGTAIL] Logout failed.', response);
      //   reload the window to clear the cookie that have immediate expiry. If so some reason, the request failed but the cookies were deleted, reload the page to force
      //   a redirection.
      window.location.reload();
    })
    .catch((error) => {
      console.error('[WAGTAIL] Error during logout:', error);
    });
}

// Define session configuration
const sessionConfig = {
  timeOffsets: { passiveRenewal: window.sessionRenewalOffsetSeconds * 1000 }, // Session renewal offset in milliseconds
  apiEndpoints: {
    renewSession: window.authTokenRefreshUrl,
  },
  onRenewSuccess: (sessionExpiryTime, refreshExpiryTime) => {
    console.debug(
      `[WAGTAIL] Auth Session renewed successfully! Session: ${sessionExpiryTime} and refresh: ${refreshExpiryTime}`,
    );

    // Extend Wagtail session
    fetchWithCsrf(extendSessionURL)
      .then((extendResponse) => {
        if (!extendResponse?.ok) {
          console.error('[WAGTAIL] Wagtail session extension failed:', extendResponse);
          logout();
          return;
        }

        console.log('Wagtail session extended successfully.');
      })
      .catch((error) => {
        console.error('[WAGTAIL] Error during Wagtail session extension:', error);
        logout();
      });
  },
  onRenewFailure: (error) => {
    console.error('[WAGTAIL] Session renewal failed:', error);
    logout();
  },
  onSessionValid: (sessionExpiryTime, refreshExpiryTime) => {
    console.debug(
      `[WAGTAIL] Session is valid. Session: ${sessionExpiryTime} and refresh: ${refreshExpiryTime}`,
    );
  },
  onSessionInvalid: () => {
    console.warn('[WAGTAIL] Session is invalid.');
    logout();
  },
  onError: (error) => {
    console.error('[WAGTAIL] Error:', error);
    logout();
  },
};

const hasIdToken = !!getCookieByName('id_token');

// Only initialise the SessionManagement library if the id_token cookie
// is present implying the user is logged in via AWS Cognito
if (hasIdToken) {
  // Initialise the SessionManagement library
  SessionManagement.init(sessionConfig);

  // These will be fetched from localStorage which is set by the auth service before redirect.
  // If they do not exist, then the session is invalid and the user will be logged out.
  SessionManagement.setSessionExpiryTime(null, null);
}
