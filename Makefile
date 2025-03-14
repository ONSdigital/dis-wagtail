DESIGN_SYSTEM_VERSION=`cat .design-system-version`

.DEFAULT_GOAL := all

.EXPORT_ALL_VARIABLES:
# Default to development config if DJANGO_SETTINGS_MODULE is not set
DJANGO_SETTINGS_MODULE ?= cms.settings.dev

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
	poetry run coverage run ./manage.py test --parallel --settings=cms.settings.test --shuffle
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
		oxsecurity/megalinter-cupcake:v8

.PHONY: load-design-system-templates
load-design-system-templates:  ## Load the design system templates
	./scripts/load-design-system-templates.sh $(DESIGN_SYSTEM_VERSION)

.PHONY: load-topics
load-topics:  ## Load our fixture of taxonomy topics
	poetry run python ./manage.py loaddata cms/taxonomy/fixtures/topics.json

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
	poetry run python ./manage.py runserver 0:8000

.PHONY: dev-init
dev-init: load-design-system-templates collectstatic makemigrations migrate load-topics createsuperuser  ## Run the pre-run setup scripts

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

# Aliases
.PHONY: start
start: compose-up
.PHONY: stop
stop: compose-stop
.PHONY: shell
shell: docker-shell
.PHONY: run
run: runserver


# The following is a temporary build script until a Concourse CI pipeline exists
# It is just designed for building a production ready image using --target=web
# To use these commands you will need AWS access and your profiles configured correctly
# If using the defaults you will need access to the dp-ci AWS account

DOCKERFILE ?= Dockerfile
ECR_REPO_NAMESPACE := dis/apps
ECR_REPO := $(ECR_REPO_NAMESPACE)/dis-wagtail-main
ECR_PROFILE_NAME ?= dp-ci
ECR_AWS_ACCOUNT_ID := $(shell aws sts get-caller-identity --query "Account" --output text --profile $(ECR_PROFILE_NAME))
AWS_REGION ?= eu-west-2
ECR_REGISTRY := $(ECR_AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com

.PHONY: create_ecr_repo
create_ecr_repo:
	@echo "Ensuring ECR repository exists: $(ECR_REPO)..."
	@if ! aws ecr describe-repositories --repository-names $(ECR_REPO) --region $(AWS_REGION) --profile $(ECR_PROFILE_NAME) > /dev/null 2>&1; then \
		echo "🚀 Repository $(ECR_REPO) does not exist. Creating..."; \
		REPO_ARN=$$(aws ecr create-repository --repository-name $(ECR_REPO) --image-tag-mutability IMMUTABLE --image-scanning-configuration scanOnPush=true --region $(AWS_REGION) --profile $(ECR_PROFILE_NAME) --query 'repository.repositoryArn' --output text); \
		echo "✅ Repository created successfully! ARN: $$REPO_ARN"; \
	else \
		echo "✅ Repository $(ECR_REPO) already exists."; \
	fi

.PHONY: check_ecr
check_ecr:
	@echo "Checking if ECR repository $(ECR_REPO) exists..."
	@if ! aws ecr describe-repositories --repository-names $(ECR_REPO) --region $(AWS_REGION) --profile $(ECR_PROFILE_NAME) > /dev/null 2>&1; then \
		echo "❌ Repository $(ECR_REPO) does not exist. Run 'make create_ecr_repo' first."; \
		exit 1; \
	fi
	@echo "✅ Repository $(ECR_REPO) exists."
	@echo "Checking if tag '$(TAG)' exists in ECR..."
	@if aws ecr describe-images --repository-name $(ECR_REPO) --region $(AWS_REGION) --profile $(ECR_PROFILE_NAME) --query 'imageDetails[?imageTags[?contains(@, `$(TAG)`)]].imageTags' --output text | grep -q $(TAG); then \
		echo "❌ Image with tag '$(TAG)' already exists in ECR repository $(ECR_REPO). Exiting."; \
		exit 1; \
	fi
	@echo "✅ Tag '$(TAG)' is available for use."

.PHONY: build_ecr_local
build_ecr_local:
	docker build -t $(ECR_REPO):$(TAG) --target=web -f $(DOCKERFILE) .
	docker tag $(ECR_REPO):$(TAG) $(ECR_REPO):latest

.PHONY: build_ecr_remote
build_ecr_remote:
	@$(MAKE) create_ecr_repo
	@$(MAKE) check_ecr
	docker build -t $(ECR_REGISTRY)/$(ECR_REPO):$(TAG) --target=web -f $(DOCKERFILE) .
	docker tag $(ECR_REGISTRY)/$(ECR_REPO):$(TAG) $(ECR_REGISTRY)/$(ECR_REPO):latest

.PHONY: push_ecr
push_ecr:
	@$(MAKE) build_ecr_remote
	@echo "🛠️  Logging into ECR..."
	@aws ecr get-login-password --region $(AWS_REGION) --profile $(ECR_PROFILE_NAME) | docker login --username AWS --password-stdin $(ECR_REGISTRY) || (echo "❌ Failed to log in to ECR"; exit 1)

	@echo "🚀 Pushing $(ECR_REGISTRY)/$(ECR_REPO):$(TAG)..."
	@docker push $(ECR_REGISTRY)/$(ECR_REPO):$(TAG) || (echo "❌ Failed to push $(ECR_REGISTRY)/$(ECR_REPO):$(TAG)"; exit 1)
	@echo "✅ Successfully pushed $(ECR_REGISTRY)/$(ECR_REPO):$(TAG)"

	@if aws ecr describe-images --repository-name $(ECR_REPO) --profile $(ECR_PROFILE_NAME) --image-ids imageTag=latest > /dev/null 2>&1; then \
		echo "🗑️  Deleting remote 'latest' tag..."; \
		output=$$(aws ecr batch-delete-image --repository-name $(ECR_REPO) --profile $(ECR_PROFILE_NAME) --image-ids imageTag=latest --output json); \
		failures=$$(echo "$$output" | jq -r '.failures | length'); \
		if [ "$$failures" -eq 0 ]; then \
			echo "✅ 'latest' Tag deleted!"; \
		else \
			echo "❌ Tag deletion for 'latest' failed, this means the image currently tagged with 'latest' is not correct, this NEEDS to be resolved"; \
			exit 1; \
		fi; \
	else \
		echo "ℹ️  Remote 'latest' tag does not exist. Skipping deletion."; \
	fi
	@echo "🚀 Pushing $(ECR_REGISTRY)/$(ECR_REPO):latest..."
	@docker push $(ECR_REGISTRY)/$(ECR_REPO):latest || (echo "❌ Failed to push $(ECR_REGISTRY)/$(ECR_REPO):latest"; exit 1)
	@echo "✅ Successfully pushed $(ECR_REGISTRY)/$(ECR_REPO):latest"
