.DEFAULT_GOAL := all

.PHONY: all
all: ## Show the available make targets.
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@fgrep "##" Makefile | fgrep -v fgrep

.PHONY: clean
clean: ## Clean the temporary files.
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .coverage
	rm -rf .ruff_cache
	rm -rf megalinter-reports

.PHONY: format
format:  ## Format the code.
	poetry run black .
	poetry run ruff check . --fix

.PHONY: lint
lint:  ## Run all linters (black/ruff/pylint/mypy).
	poetry run black --check .
	poetry run ruff check .
	make mypy

.PHONY: test
test:  ## Run the tests and check coverage.
	poetry run pytest -n auto --cov=dis_wagtail --cov-report term-missing --cov-fail-under=100

.PHONY: mypy
mypy:  ## Run mypy.
	poetry run mypy dis_wagtail

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
