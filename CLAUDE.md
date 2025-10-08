# Wikipedia Proxy Server - Project Documentation

## Project Purpose

This repository contains a simple HTTP proxy server for Wikipedia, designed to demonstrate proxy server concepts and containerized application deployment. When accessed at `<server_url>/<path>`, it fetches and serves the corresponding content from `wikipedia.org/<path>`.

## What Has Been Built

### Core Application
- **Wikipedia Proxy Server** (`wikipedia_proxy.py`)
  - Built with Flask (Python web framework)
  - Acts as a transparent proxy to wikipedia.org
  - Forwards all paths and query parameters
  - Handles HTTP headers appropriately
  - Returns Wikipedia content with proper content types

### Containerization Setup
- **Podman/Docker Support**
  - Fully containerized application using Python 3.11 slim base image
  - Production and development container configurations
  - Multi-stage deployment options
  - Platform-agnostic container setup

### Project Structure
```
/Users/pachu/code/alternate-reality/
├── wikipedia_proxy.py          # Main proxy server application
├── requirements.txt            # Python dependencies (Flask, requests)
├── Dockerfile                  # Container image definition
├── docker-compose.yml          # Production compose configuration
├── docker-compose.dev.yml      # Development compose with hot reloading
├── Makefile                    # Convenience commands
├── README.md                   # User documentation
├── .dockerignore              # Build exclusions
└── CLAUDE.md                  # This file - project documentation
```

## Technical Stack

- **Language**: Python 3.11
- **Web Framework**: Flask 3.0.0
- **HTTP Client**: Requests 2.31.0
- **Container Runtime**: Podman (Docker-compatible)
- **Container Orchestration**: podman-compose (docker-compose compatible)

## How It Works

1. The Flask server listens on port 8000
2. When a request comes in for any path, the proxy:
   - Constructs the corresponding wikipedia.org URL
   - Forwards the request with appropriate headers
   - Fetches the content from Wikipedia
   - Returns the content to the client with proper headers

## Running the Application

### Prerequisites
- Podman or Docker installed
- (Optional) podman-compose for compose files
- (Optional) Make for using convenience commands

### Production Deployment

#### Option 1: Using Make (Recommended)
```bash
make build    # Build the container image
make run      # Run the container
make logs     # View logs
make stop     # Stop and remove container
```

#### Option 2: Using Podman Directly
```bash
# Build
podman build -t wikipedia-proxy:latest .

# Run
podman run -d --name wikipedia-proxy -p 8000:8000 wikipedia-proxy:latest

# View logs
podman logs -f wikipedia-proxy

# Stop
podman stop wikipedia-proxy && podman rm wikipedia-proxy
```

#### Option 3: Using Compose
```bash
# Start services
podman-compose up -d

# View logs
podman-compose logs -f

# Stop services
podman-compose down
```

### Development Mode

For development with hot code reloading:

```bash
# Using Make
make dev

# Using compose
podman-compose -f docker-compose.dev.yml up

# Using podman with volume mount
podman run -it --rm \
    -p 8000:8000 \
    -v ./wikipedia_proxy.py:/app/wikipedia_proxy.py:z \
    --name wikipedia-proxy-dev \
    wikipedia-proxy:latest
```

## Best Practices

### Container Management
1. **Always clean up**: Use `make stop` or `podman stop/rm` to clean up containers
2. **Check port conflicts**: Ensure port 8000 is free before running
3. **Use the Makefile**: Provides consistent commands and reduces errors
4. **Monitor logs**: Use `make logs` or `podman logs -f` to debug issues

### Development Workflow
1. **Use dev mode**: Mount your local code for rapid iteration
2. **Test in container**: Always test changes in the containerized environment
3. **Rebuild after dependency changes**: Run `make build` after updating requirements.txt

### Production Considerations
1. **Don't use Flask's debug server**: Consider adding a production WSGI server (gunicorn, uwsgi)
2. **Add health checks**: Implement health check endpoints for container orchestration
3. **Configure logging**: Set up proper logging for production monitoring
4. **Add rate limiting**: Protect against abuse when exposed to internet
5. **Use environment variables**: For configuration (ports, timeouts, etc.)

## Testing the Proxy

### Basic Test
```bash
# Test Wikipedia main page
curl -I http://localhost:8000/wiki/Main_Page

# Test specific article
curl http://localhost:8000/wiki/Python_(programming_language)

# Using Make
make test
```

### Browser Access
Open in your browser:
- http://localhost:8000/wiki/Main_Page
- http://localhost:8000/wiki/Docker_(software)
- Any Wikipedia path: http://localhost:8000/<wikipedia-path>

## Architecture Decisions

### Why Flask?
- Simple and lightweight for a proxy server
- Easy to understand and modify
- Good for demonstration purposes
- Extensive documentation and community support

### Why Podman?
- Docker-compatible but daemonless
- Better security model (rootless containers)
- Direct systemd integration
- Same commands as Docker (easy transition)

### Container Strategy
- **Slim base image**: Reduces attack surface and image size
- **Non-root user**: Should be added for production (security best practice)
- **Single responsibility**: Container does one thing - proxy Wikipedia
- **Configuration via environment**: Prepared for env-based config

## Future Enhancements

Potential improvements for production use:

1. **Performance**
   - Add caching layer (Redis/Memcached)
   - Implement connection pooling
   - Add async request handling

2. **Security**
   - Add rate limiting
   - Implement request filtering
   - Add authentication if needed
   - Run as non-root user in container

3. **Features**
   - Content modification/filtering
   - Multiple backend support
   - Request/response logging
   - Metrics and monitoring endpoints

4. **Operations**
   - Health check endpoint
   - Graceful shutdown handling
   - Configuration via environment variables
   - Kubernetes/OpenShift manifests

## Troubleshooting

### Port Already in Use
```bash
# Check what's using port 8000
lsof -i :8000

# Kill the process (replace PID)
kill <PID>
```

### Container Won't Start
```bash
# Check existing containers
podman ps -a

# Remove old container
podman rm wikipedia-proxy

# Check logs
podman logs wikipedia-proxy
```

### Module Import Errors
```bash
# Rebuild the container
make clean
make build
```

## License and Attribution

This is a demonstration project created for educational purposes. Wikipedia content belongs to Wikimedia Foundation and is subject to their terms of service.

## Summary

This project demonstrates:
- Building a simple HTTP proxy server in Python
- Containerizing a Python application with Podman/Docker
- Creating development and production container configurations
- Implementing container best practices
- Providing comprehensive tooling for container management

The setup is intentionally simple to serve as a learning tool and starting point for more complex proxy server implementations.
- always run things inside podman! including tests!