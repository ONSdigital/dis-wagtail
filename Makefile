DESIGN_SYSTEM_VERSION=`cat .design-system-version`


.DEFAULT_GOAL := all

.EXPORT_ALL_VARIABLES:
# Default to development config if DJANGO_SETTINGS_MODULE is not set
DJANGO_SETTINGS_MODULE ?= cms.settings.dev
# Default web port for local development
WEB_PORT ?= 8000

.PHONY: all
all: ## Show the available make targets.
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@grep -E '^[0-9a-zA-Z_-]+:.*? .*$$'  \
		$(MAKEFILE_LIST)  \
		| awk 'BEGIN { FS=":.*?## " }; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'  \
		| sort

.PHONY: clean
clean: ## Clean the temporary files.
	rm -rf .mypy_cache
	rm -rf .coverage
	rm -rf .ruff_cache
	rm -rf megalinter-reports

.PHONY: format
format: format-py format-html format-frontend ## Format the code.

.PHONY: format-py
format-py:  ## Format the Python code
	poetry run ruff format .
	poetry run ruff check . --fix

.PHONY: format-html
format-html:  ## Format the HTML code
	find cms/ -name '*.html' | xargs poetry run djhtml

.PHONY: format-frontend
format-frontend:  ## Format front-end files (CSS, JS, YAML, MD)
	npm run format

.PHONY: npm-build
npm-build: ## Build the front-end assets
	. $$HOME/.nvm/nvm.sh; nvm use; npm run build

.PHONY: lint
lint: lint-py lint-html lint-frontend lint-migrations ## Run all linters (python, html, front-end, migrations)

.PHONY: lint-py
lint-py:  ## Run all Python linters (ruff/pylint/mypy).
	poetry run ruff check .
	poetry run ruff format --check .
	find . -type f -name "*.py" | xargs poetry run pylint --reports=n --output-format=colorized --rcfile=.pylintrc --django-settings-module=cms.settings.production -j 0
	make mypy

.PHONY: lint-html
lint-html:  ## Run HTML Linters
	find cms/ -name '*.html' | xargs poetry run djhtml --check

.PHONY: lint-frontend
lint-frontend:  ## Run front-end linters
	npm run lint

.PHONY: lint-migrations
lint-migrations: ## Run django-migration-linter
	poetry run python manage.py lintmigrations --quiet ignore ok

.PHONY: test
test:  ## Run the tests and check coverage.
	poetry run coverage erase
	COVERAGE_CORE=sysmon poetry run coverage run ./manage.py test --parallel --settings=cms.settings.test --shuffle
	poetry run coverage combine
	poetry run coverage report --fail-under=90

.PHONY: mypy
mypy:  ## Run mypy.
	poetry run mypy cms/ .github/*.py

.PHONY: pa11y
pa11y:  ## Run pa11y accessibility tests against the sitemap
	pa11y-ci --sitemap http://localhost:$(WEB_PORT)/sitemap.xml --config ./pa11y.config.js

.PHONY: install
install:  ## Install the dependencies excluding dev.
	npm install --production
	poetry install --only main --no-root

.PHONY: install-dev
install-dev:  ## Install the dependencies including dev.
	npm ci
	poetry install --no-root

.PHONY: megalint
megalint:  ## Run the mega-linter.
	docker run --platform linux/amd64 --rm \
		-v /var/run/docker.sock:/var/run/docker.sock:rw \
		-v $(shell pwd):/tmp/lint:rw \
		ghcr.io/oxsecurity/megalinter-cupcake:v9

.PHONY: load-design-system-templates
load-design-system-templates:  ## Load the design system templates
	./scripts/load-design-system-templates.sh $(DESIGN_SYSTEM_VERSION)

.PHONY: load-topics
load-topics:  ## Load our fixture of taxonomy topics
	poetry run python ./manage.py loaddata cms/taxonomy/fixtures/topics.json

# Docker and docker compose make commands

.PHONY: compose-build
compose-build: load-design-system-templates  ## Build the main application's Docker container
	docker compose build --build-arg="GIT_COMMIT=$(shell git rev-parse HEAD)" --build-arg="BUILD_TIME=$(shell date +%s)"

.PHONY: compose-pull
compose-pull: ## Pull Docker containers
	docker compose pull

.PHONY: compose-up
compose-up:  ## Start Docker containers
	docker compose up --detach

.PHONY: compose-down
compose-down:   ## Stop and remove Docker containers and networks
	docker compose down --volumes

.PHONY: compose-stop
compose-stop:  ## Stop Docker containers
	docker compose stop

.PHONY: docker-shell
docker-shell:  ## SSH into the main application's Docker container
	docker compose exec web bash

# Docker and docker compose make commands for the dev containers

.PHONY:	compose-dev-pull
compose-dev-pull: ## Pull dev Docker containers
	docker compose -f docker-compose-dev.yml pull

.PHONY: compose-dev-up
compose-dev-up:  ## Start dev Docker containers
	docker compose -f docker-compose-dev.yml up --detach

.PHONY: compose-dev-stop
compose-dev-stop: ## Stop dev Docker containers
	docker compose -f docker-compose-dev.yml stop

.PHONY: compose-dev-down
compose-dev-down: ## Stop and remove dev Docker containers and networks
	docker compose -f docker-compose-dev.yml down

# Django make command

.PHONY: makemigrations-check
makemigrations-check: ## Check whether there are new migrations to be generated
	poetry run python ./manage.py makemigrations --check

.PHONY: makemigrations
makemigrations: ## Generate new migrations
	poetry run python ./manage.py makemigrations

.PHONY: collectstatic
collectstatic:  ## Collect static files from all Django apps
	poetry run python ./manage.py collectstatic --verbosity 0 --noinput --clear

.PHONY: migrate
migrate: ## Apply the database migrations
	poetry run python ./manage.py locked_migrate

.PHONY: createsuperuser
createsuperuser: ## Create a super user with a default username and password
	poetry run python ./manage.py shell -c "from cms.users.models import User;(not User.objects.filter(username='admin').exists()) and User.objects.create_superuser('admin', 'super@example.com', 'changeme')"

.PHONY: runserver
runserver: ## Run the Django application locally
	poetry run python ./manage.py runserver 0:$(WEB_PORT)

.PHONY: dev-init
dev-init: load-design-system-templates npm-build collectstatic compilemessages makemigrations migrate load-topics createsuperuser ## Run the pre-run setup scripts
	## Set all Wagtail sites to our development port
	poetry run python manage.py shell -c "from wagtail.models import Site; Site.objects.all().update(port=$(WEB_PORT))"

.PHONY: functional-tests-up
functional-tests-up:  ## Start the functional tests docker compose dependencies
	docker compose -f functional_tests/docker-compose.yml up -d

.PHONY: functional-tests-dev-up
functional-tests-dev-up:  ## Start the functional tests docker compose dependencies and dev app
	docker compose -f functional_tests/docker-compose-dev.yml up -d

.PHONY: functional-tests-down
functional-tests-down:  ## Stop the functional tests docker compose dependencies (and dev app if running)
	docker compose -f functional_tests/docker-compose-dev.yml down

.PHONY: functional-tests-run
functional-tests-run: load-design-system-templates collectstatic ## Only run the functional tests (dependencies must be run separately)
	# Run migrations to work around Django bug (#35967)
	poetry run ./manage.py migrate --noinput --settings cms.settings.functional_test
	poetry run behave functional_tests

.PHONY: functional-tests
functional-tests: functional-tests-up functional-tests-run functional-tests-down  ## Run the functional tests with dependencies (all in one)

.PHONY: playwright-install
playwright-install:  ## Install Playwright dependencies
	poetry run playwright install --with-deps

.PHONY: makemessages
makemessages:  ## We currently just require Welsh (cy), change to -a for all languages
	poetry run python ./manage.py makemessages --locale cy --ignore "node_modules/*" --ignore ".venv"

.PHONY: compilemessages
compilemessages:
	poetry run python ./manage.py compilemessages

# Aliases
.PHONY: start
start: compose-up
.PHONY: stop
stop: compose-stop
.PHONY: shell
shell: docker-shell
.PHONY: run
run: runserver
