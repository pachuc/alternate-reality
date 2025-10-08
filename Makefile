.PHONY: build run stop clean logs shell dev test test-cov test-verbose format lint test-proxy compose-up compose-down build-test

# Build the container image
build:
	podman build -f docker/Dockerfile -t wikipedia-proxy:latest .

# Build test container image
build-test:
	podman build -f docker/Dockerfile.dev -t wikipedia-proxy-test:latest .

# Run the container (automatically loads .env if it exists)
run:
	@if [ -f .env ]; then \
		echo "Loading environment from .env file..."; \
		set -a; source .env; set +a; \
		podman run -d --name wikipedia-proxy -p 8000:8000 \
			-e ANTHROPIC_API_KEY="$${ANTHROPIC_API_KEY:-}" \
			-e ENABLE_LLM_REWRITE="$${ENABLE_LLM_REWRITE:-false}" \
			-e CLAUDE_MODEL="$${CLAUDE_MODEL:-claude-3-haiku-20240307}" \
			-e MAX_REWRITE_TOKENS="$${MAX_REWRITE_TOKENS:-1000}" \
			wikipedia-proxy:latest; \
	else \
		podman run -d --name wikipedia-proxy -p 8000:8000 \
			-e ANTHROPIC_API_KEY="$${ANTHROPIC_API_KEY:-}" \
			-e ENABLE_LLM_REWRITE="$${ENABLE_LLM_REWRITE:-false}" \
			-e CLAUDE_MODEL="$${CLAUDE_MODEL:-claude-3-haiku-20240307}" \
			-e MAX_REWRITE_TOKENS="$${MAX_REWRITE_TOKENS:-1000}" \
			wikipedia-proxy:latest; \
	fi

# Run with docker-compose (using podman-compose)
compose-up:
	podman-compose -f docker/docker-compose.yml up -d

# Stop and remove with docker-compose
compose-down:
	podman-compose -f docker/docker-compose.yml down

# Development mode - mounts local code (automatically loads .env if it exists)
dev:
	@if [ -f .env ]; then \
		echo "Loading environment from .env file..."; \
		set -a; source .env; set +a; \
		podman run -it --rm \
			-p 8000:8000 \
			-v ./src:/app/src:z \
			-e ANTHROPIC_API_KEY="$${ANTHROPIC_API_KEY:-}" \
			-e ENABLE_LLM_REWRITE="$${ENABLE_LLM_REWRITE:-false}" \
			-e CLAUDE_MODEL="$${CLAUDE_MODEL:-claude-3-haiku-20240307}" \
			-e MAX_REWRITE_TOKENS="$${MAX_REWRITE_TOKENS:-1000}" \
			--name wikipedia-proxy-dev \
			wikipedia-proxy:latest; \
	else \
		podman run -it --rm \
			-p 8000:8000 \
			-v ./src:/app/src:z \
			-e ANTHROPIC_API_KEY="$${ANTHROPIC_API_KEY:-}" \
			-e ENABLE_LLM_REWRITE="$${ENABLE_LLM_REWRITE:-false}" \
			-e CLAUDE_MODEL="$${CLAUDE_MODEL:-claude-3-haiku-20240307}" \
			-e MAX_REWRITE_TOKENS="$${MAX_REWRITE_TOKENS:-1000}" \
			--name wikipedia-proxy-dev \
			wikipedia-proxy:latest; \
	fi

# Stop the container
stop:
	podman stop wikipedia-proxy || true
	podman rm wikipedia-proxy || true

# Clean up images and containers
clean:
	podman stop wikipedia-proxy || true
	podman rm wikipedia-proxy || true
	podman stop wikipedia-proxy-dev || true
	podman rm wikipedia-proxy-dev || true
	podman rmi wikipedia-proxy:latest || true
	podman rmi wikipedia-proxy-test:latest || true

# View logs
logs:
	podman logs -f wikipedia-proxy

# Shell into running container
shell:
	podman exec -it wikipedia-proxy /bin/bash

# Test the running proxy (requires running container)
test-proxy:
	@echo "Testing Wikipedia proxy on http://localhost:8000..."
	@podman run --rm --network host curlimages/curl:latest \
		curl -I http://localhost:8000/wiki/Main_Page

# Run unit tests in container
test: build-test
	podman run --rm \
		-v ./src:/app/src:z \
		-v ./tests:/app/tests:z \
		-v ./config:/app/config:z \
		wikipedia-proxy-test:latest pytest -v

# Run tests with coverage in container
test-cov: build-test
	podman run --rm \
		-v ./src:/app/src:z \
		-v ./tests:/app/tests:z \
		-v ./config:/app/config:z \
		-v ./htmlcov:/app/htmlcov:z \
		wikipedia-proxy-test:latest \
		pytest --cov=src --cov-report=term-missing --cov-report=html

# Run tests in verbose mode in container
test-verbose: build-test
	podman run --rm \
		-v ./src:/app/src:z \
		-v ./tests:/app/tests:z \
		-v ./config:/app/config:z \
		wikipedia-proxy-test:latest pytest -vv

# Format code in container
format: build-test
	podman run --rm \
		-v ./src:/app/src:z \
		-v ./tests:/app/tests:z \
		wikipedia-proxy-test:latest \
		black src tests

# Lint code in container
lint: build-test
	podman run --rm \
		-v ./src:/app/src:z \
		-v ./tests:/app/tests:z \
		wikipedia-proxy-test:latest \
		flake8 src tests --max-line-length=100 --ignore=E501

# Run all quality checks (tests, format check, lint)
check: test lint
	@echo "All checks passed!"

# Quick test without rebuilding image (assumes test image exists)
test-quick:
	podman run --rm \
		-v ./src:/app/src:z \
		-v ./tests:/app/tests:z \
		-v ./config:/app/config:z \
		wikipedia-proxy-test:latest pytest -v

# Interactive shell in test container for debugging
test-shell: build-test
	podman run -it --rm \
		-v ./src:/app/src:z \
		-v ./tests:/app/tests:z \
		-v ./config:/app/config:z \
		wikipedia-proxy-test:latest /bin/bash