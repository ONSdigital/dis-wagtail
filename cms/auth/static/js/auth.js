/* eslint-disable no-undef */
/* eslint-disable no-console */

function getCookieValue(name) {
  return (
    document.cookie
      .split(';')
      .map((cookie) => cookie.trim().split('='))
      .find(([key]) => key === name)?.[1] || null
  );
}

function decodeJWT(token) {
  try {
    const [, payload] = token.split('.');
    if (!payload) throw new Error('Invalid JWT format');
    const json = atob(payload.replace(/-/g, '+').replace(/_/g, '/'));
    return JSON.parse(json);
  } catch (error) {
    console.error('Error decoding JWT:', error);
    return null;
  }
}

async function fetchWithCsrf(url, method = 'POST', body = null, headers = {}) {
  const csrfToken = getCookieValue(window.csrfCookieName);
  if (!csrfToken) {
    console.error('CSRF token not found.');
    return null;
  }

  const defaultHeaders = {
    'Content-Type': 'application/json',
    [window.csrfHeaderName]: csrfToken,
  };

  try {
    const response = await fetch(url, {
      method,
      headers: { ...defaultHeaders, ...headers },
      credentials: 'include',
      body: body ? JSON.stringify(body) : null,
    });
    return response;
  } catch (error) {
    console.error(`Error during ${method} request to ${url}:`, error);
    return null;
  }
}

async function logout(config) {
  console.log('Attempting logout...');
  const response = await fetchWithCsrf(config.LOGOUT_URL);
  if (response?.ok) {
    console.log('Logout successful.');
    window.location.href = response.redirected ? response.url : config.baseURL;
  } else {
    console.error('Logout failed.');
  }
}

async function refreshAuthToken(config) {
  console.log('Refreshing auth token...');
  try {
    const refreshResponse = await fetch(config.AUTH_TOKEN_REFRESH_URL, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
    });

    if (!refreshResponse.ok) {
      console.error('Auth token refresh failed:', await extractErrorDetails(refreshResponse));
      await logout(config);
      return;
    }

    console.log('Auth token refreshed successfully.');

    // Extend Django session
    const extendResponse = await fetchWithCsrf(config.EXTEND_SESSION_URL);

    if (!extendResponse.ok) {
      console.error('Django session extension failed:');
      await logout(config);
      return;
    }

    console.log('Django session extended successfully.');
  } catch (error) {
    console.error('Error refreshing auth token:', error);
    await logout(config);
  }
}

// Main session management logic
async function handleSession(config) {
  const idToken = getCookieValue('id_token');
  if (!idToken) {
    console.log('No id_token cookie found. No action needed.');
    return;
  }

  const payload = decodeJWT(idToken);
  if (!payload || typeof payload.exp !== 'number') {
    console.error('Invalid JWT or missing expiration claim.');
    await logout(config);
    return;
  }

  // Note: This implementation assumes that the expiration times (exp) for the id_token and access_token are the same.
  // However, this is not the case in the current CMS.
  // Further discussion is needed to address this discrepancy—either by aligning their expiration times.
  // or by providing an alternative mechanism, such as an API or cookie, to indicate the tokens' expiry times.
  // This is also now aware of the expiration time of the refresh token.

  // Expiry time is in seconds since Unix epoch
  const currentTime = Math.floor(Date.now() / 1000);
  const timeToExpiry = payload.exp - currentTime;

  console.log('Session expires in', timeToExpiry, 'seconds');

  if (timeToExpiry <= config.EXPIRY_BUFFER_SECONDS) {
    console.log('Token nearing expiry. Refreshing...');
    await refreshAuthToken(config);
  } else {
    console.log('Token is valid and not expiring soon.');
  }
}

// Attach user activity event listeners
function attachUserActivityListeners(callback) {
  const events = ['mousemove', 'mousedown', 'keydown', 'scroll', 'touchstart', 'load'];
  events.forEach((event) => window.addEventListener(event, callback, { passive: true }));
}

// Main entry point
(function initSessionManagement() {
  const config = {
    baseURL: window.location.origin,
    wagtailAdminHomePath: window.wagtailAdminHomePath,
    CSRF_COOKIE_NAME: window.csrfCookieName,
    CSRF_HEADER_NAME: window.csrfHeaderName,
    EXPIRY_BUFFER_SECONDS: 5 * 60,
    AUTH_TOKEN_REFRESH_URL: window.authTokenRefreshUrl || null,
    LOGOUT_URL: `${window.location.origin}/${window.wagtailAdminHomePath}logout/`,
    EXTEND_SESSION_URL: `${window.location.origin}/${window.wagtailAdminHomePath}extend-session/`,
  };

  let lastChecked = 0;

  const sessionManager = async () => {
    const now = Date.now();
    if (now - lastChecked < 60 * 1000) {
      console.log('Session checked less than a minute ago. Skipping.');
      return;
    }
    lastChecked = now;
    console.log('Checking session due to user activity...');

    try {
      await handleSession(config);
    } catch (error) {
      console.error('Error handling session:', error);
      await logout(config);
    }
  };

  attachUserActivityListeners(sessionManager);
  console.log('Session management initialised.');
})();
