.DEFAULT_GOAL := help

# Variables
DOCKER_IMAGE := ivantana/media-service
DOCKER_TAG := latest
COMPOSE_FILE := docker-compose.yaml

# Help target
.PHONY: help
help: ## Show this help message
	@echo "Media Service - Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Development
.PHONY: dev
dev: ## Run development server with auto-reload
	uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

.PHONY: dev-deps
dev-deps: ## Install development dependencies
	uv sync

# Docker targets
.PHONY: build
build: ## Build Docker image
	docker build -t $(DOCKER_IMAGE):$(DOCKER_TAG) .

.PHONY: build-no-cache
build-no-cache: ## Build Docker image without cache
	docker build --no-cache -t $(DOCKER_IMAGE):$(DOCKER_TAG) .

# Docker Compose targets
.PHONY: up
up: ## Start all services with docker-compose (production)
	docker-compose -f $(COMPOSE_FILE) up -d

.PHONY: up-dev
up-dev: ## Start all services for development (builds locally)
	docker-compose -f $(COMPOSE_FILE) -f docker-compose.dev.yaml up -d

.PHONY: down
down: ## Stop all services
	docker-compose -f $(COMPOSE_FILE) down

.PHONY: restart
restart: down up ## Restart all services

.PHONY: restart-dev
restart-dev: down up-dev ## Restart all services for development

.PHONY: logs
logs: ## Show logs from all services
	docker-compose -f $(COMPOSE_FILE) logs -f

.PHONY: logs-api
logs-api: ## Show logs from API service only
	docker-compose -f $(COMPOSE_FILE) logs -f media-api

.PHONY: logs-mongo
logs-mongo: ## Show logs from MongoDB service only
	docker-compose -f $(COMPOSE_FILE) logs -f mongodb

# Database targets
.PHONY: mongo-shell
mongo-shell: ## Connect to MongoDB shell
	docker-compose -f $(COMPOSE_FILE) exec mongodb mongosh -u root -p example --authenticationDatabase admin

.PHONY: mongo-start
mongo-start: ## Start only MongoDB service
	docker-compose -f $(COMPOSE_FILE) up -d mongodb

# Testing and Quality
.PHONY: test
test: ## Run tests (placeholder for now)
	@echo "No tests configured yet"

.PHONY: lint
lint: ## Run linting checks
	uv run ruff check app/
	uv run mypy app/

.PHONY: format
format: ## Format code
	uv run ruff format app/

# Cleanup targets
.PHONY: clean
clean: ## Remove Docker containers and images
	docker-compose -f $(COMPOSE_FILE) down -v --remove-orphans
	docker image rm $(DOCKER_IMAGE):$(DOCKER_TAG) 2>/dev/null || true

.PHONY: clean-volumes
clean-volumes: ## Remove Docker volumes (WARNING: This will delete data!)
	docker-compose -f $(COMPOSE_FILE) down -v

# Docker Hub targets
.PHONY: login
login: ## Login to Docker Hub
	docker login

.PHONY: push
push: build ## Build and push image to Docker Hub
	docker push $(DOCKER_IMAGE):$(DOCKER_TAG)

.PHONY: push-latest
push-latest: build ## Build and push latest tag to Docker Hub
	docker tag $(DOCKER_IMAGE):$(DOCKER_TAG) $(DOCKER_IMAGE):latest
	docker push $(DOCKER_IMAGE):latest

.PHONY: release
release: build ## Build, tag and push both latest and production images
	@echo "Building and pushing $(DOCKER_IMAGE):$(DOCKER_TAG)"
	docker push $(DOCKER_IMAGE):$(DOCKER_TAG)
	@echo "Tagging and pushing $(DOCKER_IMAGE):latest"
	docker tag $(DOCKER_IMAGE):$(DOCKER_TAG) $(DOCKER_IMAGE):latest
	docker push $(DOCKER_IMAGE):latest
	@echo "Building and pushing production image"
	docker build -t $(DOCKER_IMAGE):production -f Dockerfile .
	docker push $(DOCKER_IMAGE):production

# Production targets
.PHONY: prod-build
prod-build: ## Build production image
	docker build -t $(DOCKER_IMAGE):production -f Dockerfile .

.PHONY: prod-push
prod-push: prod-build ## Build and push production image
	docker push $(DOCKER_IMAGE):production

.PHONY: prod-up
prod-up: ## Start production services
	docker-compose -f $(COMPOSE_FILE) -f docker-compose.prod.yaml up -d
