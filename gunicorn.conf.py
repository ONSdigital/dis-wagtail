# pylint: disable=invalid-name
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

# Time out after 25 seconds by default (notably shorter than Heroku's)
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "25"))

# Load app pre-fork to save memory and worker startup time
preload_app = True
# pylint: enable=invalid-name
