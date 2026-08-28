# pylint: disable=invalid-name
import math
import os

import gunicorn

# Tell gunicorn to run our app
wsgi_app = "cms.wsgi:application"

# Replace gunicorn's 'Server' HTTP header to avoid leaking info to attackers
gunicorn.SERVER = ""

# Restart gunicorn worker processes every 1200-1250 requests
max_requests = int(os.environ.get("GUNICORN_MAX_REQUESTS", "1200"))
max_requests_jitter = int(os.environ.get("GUNICORN_MAX_REQUESTS_JITTER", "50"))

# Log to stdout
accesslog = "-"

# Time out after 25 seconds
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "25"))

# Allow the bundle publishing timeout to expire before considering a terminate "ungraceful".
# gunicorn expects an int, but the timeout is parsed as a float elsewhere so convert to preserve behavior
graceful_timeout = math.ceil(float(os.environ.get("BUNDLE_POST_PUBLISH_TIMEOUT_SECONDS", "110")))

# Load app pre-fork to save memory and worker startup time
preload_app = True
# pylint: enable=invalid-name
