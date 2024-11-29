# Note: This file is loaded on all environments, even production.

alias dj="django-admin"

if [ -n "$DEVCONTAINER" ]
then
    alias djrun="django-admin runserver 0.0.0.0:8000"
    alias djtest="python manage.py test --settings=cms.settings.test --shuffle"
    alias djrunplus="python manage.py runserver_plus 0.0.0.0:8000"
    alias honcho="honcho -f .docker/Procfile"
fi
