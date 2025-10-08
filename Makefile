.PHONY: build run stop clean logs shell dev

# Build the container image
build:
	podman build -t wikipedia-proxy:latest .

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
	podman rmi wikipedia-proxy:latest || true

# View logs
logs:
	podman logs -f wikipedia-proxy

# Shell into running container
shell:
	podman exec -it wikipedia-proxy /bin/bash

# Test the proxy
test:
	@echo "Testing Wikipedia proxy..."
	@curl -I http://localhost:8000/wiki/Main_Page