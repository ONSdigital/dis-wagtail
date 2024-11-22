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
	poetry run ruff check . --fix
	poetry run ruff format .

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

.PHONY: docker-build
docker-build: load-design-system-templates  ## Build Docker container
	docker compose pull
	docker compose build

.PHONY: docker-up
docker-up:  ## Start Docker containers
	docker compose up --detach

.PHONY: docker-stop
docker-stop:  ## Stop Docker containers
	docker compose stop

.PHONY: docker-shell
docker-shell:  ## SSH into Docker container
	docker compose exec web bash

.PHONY: docker-destroy
docker-destroy:  ## Tear down the Docker containers
	docker compose down --volumes

.PHONY: docker-dev-pull
docker-dev-pull: load-design-system-templates  ## Pull dev Docker containers
	docker compose -f docker-compose-dev.yml pull

.PHONY: docker-dev-up
docker-dev-up:  ## Start dev Docker containers
	docker compose -f docker-compose-dev.yml up --detach 

.PHONY: docker-dev-stop
docker-dev-stop: ## Stop dev Docker containers
	docker compose -f docker-compose-dev.yml stop

.PHONY: docker-dev-down
docker-dev-down: ## Stop dev Docker containers
	docker compose -f docker-compose-dev.yml down

.PHONY: check-makemigrations
check-makemigrations: ## Convenience alias to run makemigrations in venv
	poetry run python ./manage.py makemigrations --check

.PHONY: makemigrations
makemigrations: ## Convenience alias to run makemigrations in venv
	poetry run python ./manage.py makemigrations

.PHONY: collectstatic
collectstatic:  ## Convenience alias to run collectstatic in venv
	poetry run python ./manage.py collectstatic --verbosity 0 --noinput --clear
	
.PHONY: migrate
migrate: ## Convenience alias to run migrate in venv
	poetry run python ./manage.py migrate 

.PHONY: createsuperuser
createsuperuser: ## Convenience alias to run createsuperuser in venv
	poetry run python ./manage.py createsuperuser

.PHONY: runserver
runserver: # Run the Django application locally	
	poetry run python ./manage.py runserver