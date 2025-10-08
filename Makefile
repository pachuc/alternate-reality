.PHONY: build run stop clean logs shell dev test test-cov test-verbose format lint test-proxy compose-up compose-down build-test

# Build the container image
build:
	podman build -t wikipedia-proxy:latest .

# Build test container image
build-test:
	podman build -f Dockerfile.dev -t wikipedia-proxy-test:latest .

# Run the container
run:
	podman run -d --name wikipedia-proxy -p 8000:8000 wikipedia-proxy:latest

# Run with docker-compose (using podman-compose)
compose-up:
	podman-compose up -d

# Stop and remove with docker-compose
compose-down:
	podman-compose down

# Development mode - mounts local code
dev:
	podman run -it --rm \
		-p 8000:8000 \
		-v ./wikipedia_proxy.py:/app/wikipedia_proxy.py:z \
		--name wikipedia-proxy-dev \
		wikipedia-proxy:latest

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
	podman run --rm -v ./wikipedia_proxy.py:/app/wikipedia_proxy.py:z \
		-v ./test_wikipedia_proxy.py:/app/test_wikipedia_proxy.py:z \
		wikipedia-proxy-test:latest pytest -v

# Run tests with coverage in container
test-cov: build-test
	podman run --rm -v ./wikipedia_proxy.py:/app/wikipedia_proxy.py:z \
		-v ./test_wikipedia_proxy.py:/app/test_wikipedia_proxy.py:z \
		-v ./htmlcov:/app/htmlcov:z \
		wikipedia-proxy-test:latest \
		pytest --cov=wikipedia_proxy --cov-report=term-missing --cov-report=html

# Run tests in verbose mode in container
test-verbose: build-test
	podman run --rm -v ./wikipedia_proxy.py:/app/wikipedia_proxy.py:z \
		-v ./test_wikipedia_proxy.py:/app/test_wikipedia_proxy.py:z \
		wikipedia-proxy-test:latest pytest -vv

# Format code in container
format: build-test
	podman run --rm -v ./wikipedia_proxy.py:/app/wikipedia_proxy.py:z \
		-v ./test_wikipedia_proxy.py:/app/test_wikipedia_proxy.py:z \
		wikipedia-proxy-test:latest \
		black wikipedia_proxy.py test_wikipedia_proxy.py

# Lint code in container
lint: build-test
	podman run --rm -v ./wikipedia_proxy.py:/app/wikipedia_proxy.py:z \
		-v ./test_wikipedia_proxy.py:/app/test_wikipedia_proxy.py:z \
		wikipedia-proxy-test:latest \
		flake8 wikipedia_proxy.py test_wikipedia_proxy.py --max-line-length=100 --ignore=E501

# Run all quality checks (tests, format check, lint)
check: test lint
	@echo "All checks passed!"

# Quick test without rebuilding image (assumes test image exists)
test-quick:
	podman run --rm -v ./wikipedia_proxy.py:/app/wikipedia_proxy.py:z \
		-v ./test_wikipedia_proxy.py:/app/test_wikipedia_proxy.py:z \
		wikipedia-proxy-test:latest pytest -v

# Interactive shell in test container for debugging
test-shell: build-test
	podman run -it --rm -v ./wikipedia_proxy.py:/app/wikipedia_proxy.py:z \
		-v ./test_wikipedia_proxy.py:/app/test_wikipedia_proxy.py:z \
		wikipedia-proxy-test:latest /bin/bash