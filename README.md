# Wikipedia Proxy Server

A simple Python web server that acts as a proxy for Wikipedia, containerized with Podman, with AI-powered content rewriting capability.

📖 **For detailed documentation, architecture decisions, and best practices, see [CLAUDE.md](CLAUDE.md)**

## Features

- Proxies all requests to wikipedia.org
- AI-powered content rewriting using Claude (optional)
- Containerized for easy deployment
- Development and production configurations
- Simple and lightweight

## Prerequisites

- Podman (or Docker)
- podman-compose (optional, for compose files)
- Make (optional, for using Makefile commands)

## LLM Content Rewriting (Optional)

The proxy server includes scaffolding for AI-powered content rewriting using Claude. This feature is disabled by default.

### Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Set your Anthropic API key:
```bash
# Edit .env and add your API key
ANTHROPIC_API_KEY=your-actual-api-key-here
```

3. Enable LLM rewriting:
```bash
# In .env, set:
ENABLE_LLM_REWRITE=true
```

### Environment Variables

- `ANTHROPIC_API_KEY`: Your Anthropic API key (required for LLM features)
- `ENABLE_LLM_REWRITE`: Enable/disable LLM content rewriting (default: false)
- `CLAUDE_MODEL`: Claude model to use (default: claude-3-haiku-20240307)
- `MAX_REWRITE_TOKENS`: Maximum tokens for rewriting (default: 1000)

### Running with LLM Features

```bash
# Using environment variables
export ANTHROPIC_API_KEY=your-api-key
export ENABLE_LLM_REWRITE=true
make run

# Or using .env file with podman-compose
podman-compose up -d
```

**Note**: The LLM rewriting is currently a placeholder that adds a notice to pages. Full implementation coming soon!

## Quick Start

### Using Makefile

```bash
# Build the container
make build

# Run the container
make run

# Check logs
make logs

# Stop the container
make stop
```

### Using Podman directly

```bash
# Build the image
podman build -t wikipedia-proxy:latest .

# Run the container
podman run -d --name wikipedia-proxy -p 8000:8000 wikipedia-proxy:latest

# Check logs
podman logs -f wikipedia-proxy

# Stop and remove
podman stop wikipedia-proxy
podman rm wikipedia-proxy
```

### Using podman-compose

```bash
# Start services
podman-compose up -d

# View logs
podman-compose logs -f

# Stop services
podman-compose down
```

## Development

For development with hot reloading:

```bash
# Using Make
make dev

# Using podman-compose
podman-compose -f docker-compose.dev.yml up

# Using podman directly
podman run -it --rm \
    -p 8000:8000 \
    -v ./wikipedia_proxy.py:/app/wikipedia_proxy.py:z \
    --name wikipedia-proxy-dev \
    wikipedia-proxy:latest
```

## Usage

Once running, access Wikipedia content through the proxy:

```bash
# Access Wikipedia main page
http://localhost:8000/wiki/Main_Page

# Access any Wikipedia path
http://localhost:8000/<any-wikipedia-path>

# Example: Python programming language page
http://localhost:8000/wiki/Python_(programming_language)
```

## Testing

Test the proxy is working:

```bash
# Using Make
make test

# Using curl
curl http://localhost:8000/wiki/Main_Page

# Using browser
open http://localhost:8000/wiki/Main_Page
```

## Container Management

```bash
# View running containers
podman ps

# Shell into container
make shell
# or
podman exec -it wikipedia-proxy /bin/bash

# Clean up everything
make clean
```

## Project Structure

- `wikipedia_proxy.py` - Main proxy server application
- `requirements.txt` - Python dependencies (Flask, requests)
- `Dockerfile` - Container image definition
- `docker-compose.yml` - Production compose configuration
- `docker-compose.dev.yml` - Development compose configuration
- `Makefile` - Convenience commands
- `README.md` - Quick start guide (this file)
- `CLAUDE.md` - Comprehensive project documentation
- `.dockerignore` - Build exclusions

## Troubleshooting

### Port Already in Use
```bash
# Check what's using port 8000
lsof -i :8000
# Kill the process if needed
kill <PID>
```

### Container Issues
```bash
# Remove existing container
podman rm wikipedia-proxy
# Rebuild if needed
make clean && make build
```

For more troubleshooting tips, see [CLAUDE.md](CLAUDE.md#troubleshooting)

## Technical Details

- **Port**: 8000 (default)
- **Backend**: https://wikipedia.org
- **Base Image**: Python 3.11 slim
- **Framework**: Flask 3.0.0
- **HTTP Client**: Requests 2.31.0

For architecture decisions and best practices, see [CLAUDE.md](CLAUDE.md#architecture-decisions)