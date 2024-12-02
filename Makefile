DESIGN_SYSTEM_VERSION=`cat .design-system-version`

.DEFAULT_GOAL := all

.PHONY: all
all: ## Show the available make targets.
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@fgrep "##" Makefile | fgrep -v fgrep

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

.PHONY: lint
lint: lint-py lint-html lint-frontend ## Run all linters (python, html, front-end)

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

.PHONY: test
test:  ## Run the tests and check coverage.
	poetry run coverage erase
	poetry run coverage run ./manage.py test --parallel --settings=cms.settings.test
	poetry run coverage combine
	poetry run coverage report --fail-under=90

.PHONY: mypy
mypy:  ## Run mypy.
	poetry run mypy cms

.PHONY: install
install:  ## Install the dependencies excluding dev.
	poetry install --only main --no-root

.PHONY: install-dev
install-dev:  ## Install the dependencies including dev.
	poetry install --no-root

.PHONY: megalint
megalint:  ## Run the mega-linter.
	docker run --platform linux/amd64 --rm \
		-v /var/run/docker.sock:/var/run/docker.sock:rw \
		-v $(shell pwd):/tmp/lint:rw \
		oxsecurity/megalinter:v7

.PHONY: load-design-system-templates
load-design-system-templates:  ## Load the design system templates
	./scripts/load-design-system-templates.sh $(DESIGN_SYSTEM_VERSION)

# Docker and docker compose make commands

.PHONY: compose-build
compose-build: load-design-system-templates  ## Build the main application's Docker container
	docker compose build

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
	poetry run python ./manage.py migrate 

.PHONY: createsuperuser
createsuperuser: ## Create a super user with a default username and password
	poetry run python ./manage.py shell -c "from cms.users.models import User;(not User.objects.filter(username='admin').exists()) and User.objects.create_superuser('admin', 'super@example.com', 'changeme')"

.PHONY: runserver
runserver: ## Run the Django application locally	
	poetry run python ./manage.py runserver

.PHONY: dev-init 
dev-init: load-design-system-templates collectstatic makemigrations migrate createsuperuser ## Run the pre-run setup scripts
