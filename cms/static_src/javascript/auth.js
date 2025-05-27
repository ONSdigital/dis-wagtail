/* eslint-disable no-console */

import SessionManagement from 'dis-authorisation-client-js';

/** ----------------------------------------------------------------
 *  Grab the JSON produced by:
 *      {{ AUTH_CONFIG | json_script('auth-config') }}
 *  in the Jinja template (or the Python hook).
 * ----------------------------------------------------------------*/

let authConfig = {};
const configEl = document.getElementById('auth-config');

if (configEl) {
  try {
    authConfig = JSON.parse(configEl.textContent);
  } catch (e) {
    console.error('[WAGTAIL] Failed to parse <script id="auth-config">:', e);
  }
}

const {
  wagtailAdminHomePath,
  csrfCookieName,
  csrfHeaderName,
  sessionRenewalOffsetSeconds,
  authTokenRefreshUrl,
  idTokenCookieName,
} = authConfig;

const { origin } = window.location;
const logoutURL = `${origin}/${wagtailAdminHomePath}logout/`;
const extendSessionURL = `${origin}/${wagtailAdminHomePath}extend-session/`;

function getCookieByName(name) {
  console.debug('[WAGTAIL] Getting cookie by name:', name);
  const cookies = document.cookie;
  if (!cookies) {
    return null;
  }
  const cookie = cookies
    .split(';')
    .map((cookieStr) => cookieStr.trim())
    .map((cookieStr) => cookieStr.split('='))
    .find((pair) => pair[0] === name);
  return cookie ? cookie[1] : null;
}

// Performs a fetch request with CSRF protection.
const fetchWithCsrf = async (url, method = 'POST', body = null, additionalHeaders = {}) => {
  const csrfToken = getCookieByName(csrfCookieName);
  if (!csrfToken) {
    console.error('[WAGTAIL] CSRF token not found.');
    return null;
  }

  const headers = {
    'Content-Type': 'application/json',
    [csrfHeaderName]: csrfToken,
    ...additionalHeaders,
  };

  const config = {
    method,
    headers,
    credentials: 'include',
    ...(body && { body: JSON.stringify(body) }),
  };

  try {
    return await fetch(url, config);
  } catch (error) {
    console.error(`[WAGTAIL] Error during ${method} request to ${url}:`, error);
    return null;
  }
};

// Initiates the logout process and handles redirection.
const logout = async () => {
  console.info('[WAGTAIL] Initiating logout...');
  try {
    const response = await fetchWithCsrf(logoutURL);
    if (response?.ok) {
      const redirectURL = response.redirected ? response.url : origin;
      console.info('[WAGTAIL] Logout successful. Redirecting to:', redirectURL);
      window.location.href = redirectURL;
    } else {
      console.error('[WAGTAIL] Logout failed:', response);
      // Reload the page to handle any session inconsistencies.
      window.location.reload();
    }
  } catch (error) {
    console.error('[WAGTAIL] Exception during logout:', error);
  }
};

// Session configuration
const sessionConfig = {
  timeOffsets: { passiveRenewal: parseInt(sessionRenewalOffsetSeconds, 10) * 1000 }, // milliseconds
  apiEndpoints: {
    renewSession: authTokenRefreshUrl,
  },
  onRenewSuccess: async (sessionExpiryTime, refreshExpiryTime) => {
    console.debug(
      `[WAGTAIL] Session renewed! (Session: ${sessionExpiryTime}, Refresh: ${refreshExpiryTime})`,
    );
    try {
      const extendResponse = await fetchWithCsrf(extendSessionURL);
      if (extendResponse?.ok) {
        console.info('[WAGTAIL] Wagtail session extended successfully.');
      } else {
        console.error('[WAGTAIL] Session extension failed:', extendResponse);
        await logout();
      }
    } catch (error) {
      console.error('[WAGTAIL] Error extending session:', error);
      await logout();
    }
  },
  onRenewFailure: async (error) => {
    console.error('[WAGTAIL] Session renewal failed:', error);
    await logout();
  },
  onSessionValid: (sessionExpiryTime, refreshExpiryTime) => {
    console.debug(
      `[WAGTAIL] Session valid. (Session: ${sessionExpiryTime}, Refresh: ${refreshExpiryTime})`,
    );
  },
  onSessionInvalid: async () => {
    console.warn('[WAGTAIL] Session invalid.');
    await logout();
  },
  onError: async (error) => {
    console.error('[WAGTAIL] General error:', error);
    await logout();
  },
};

// Initialise SessionManagement only if the user is logged in via Cognito (indicated by the presence of an id_token cookie).
// Don't load if it's in an iframe (e.g. the Wagtail admin interface preview).
if (window.self === window.top && getCookieByName(idTokenCookieName)) {
  SessionManagement.init(sessionConfig);

  // These will be fetched from localStorage which is set by the auth service before redirect.
  // If they do not exist, then the session is invalid and the user will be logged out.
  // Only clear if *neither* value is set, i.e. brand-new tab with no prior expiry info:
  if (
    !localStorage.getItem('session_expiry_time') &&
    !localStorage.getItem('refresh_expiry_time')
  ) {
    SessionManagement.setSessionExpiryTime(null, null);
  }
}
