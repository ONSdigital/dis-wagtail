# The following is a temporary build script until a Concourse CI pipeline exists
# It is just designed for building a production ready image using --target=web
# To use these commands you will need AWS access and your profiles configured correctly
# If using the defaults you will need access to the dp-ci AWS account

DOCKERFILE := ../Dockerfile
ECR_REPO_NAMESPACE := dis/apps
ECR_REPO := $(ECR_REPO_NAMESPACE)/dis-wagtail-cms
ECR_PROFILE_NAME ?= dp-ci
ECR_AWS_ACCOUNT_ID := $(shell aws sts get-caller-identity --query "Account" --output text --profile $(ECR_PROFILE_NAME))
AWS_REGION ?= eu-west-2
ECR_REGISTRY := $(ECR_AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com
BUILD_ARGS := --build-arg="GIT_COMMIT=$(shell git rev-parse HEAD)" --build-arg="BUILD_TIME=$(shell date +%s)"

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

.PHONY: build_ecr_remote
build_ecr_remote:
	@$(MAKE) create_ecr_repo
	@$(MAKE) check_ecr
	docker build -t $(ECR_REGISTRY)/$(ECR_REPO):$(TAG) --target=web -f $(DOCKERFILE) $(BUILD_ARGS) ../
	docker tag $(ECR_REGISTRY)/$(ECR_REPO):$(TAG) $(ECR_REGISTRY)/$(ECR_REPO):latest

.PHONY: push_ecr
push_ecr:
	@$(MAKE) build_ecr_remote
	@echo "🛠️  Logging into ECR..."
	@aws ecr get-login-password --region $(AWS_REGION) --profile $(ECR_PROFILE_NAME) | docker login --username AWS --password-stdin $(ECR_REGISTRY) || (echo "❌ Failed to log in to ECR"; exit 1)

	@echo "🚀 Pushing $(ECR_REGISTRY)/$(ECR_REPO):$(TAG)..."
	@docker push $(ECR_REGISTRY)/$(ECR_REPO):$(TAG) || (echo "❌ Failed to push $(ECR_REGISTRY)/$(ECR_REPO):$(TAG)"; exit 1)
	@echo "✅ Successfully pushed $(ECR_REGISTRY)/$(ECR_REPO):$(TAG)"
