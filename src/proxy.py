#!/usr/bin/env python3
"""
Wikipedia Proxy Server

A simple HTTP proxy that forwards requests to Wikipedia and rewrites content.
"""

import os
import requests
from flask import Flask, Response, request, redirect

from src import html_processing

app = Flask(__name__)

# Wikipedia base URL - use en.wikipedia.org directly
WIKIPEDIA_BASE = "https://en.wikipedia.org"


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def proxy(path):
    """
    Proxy all requests to Wikipedia
    """
    # Special handling for Wikimedia resources
    if path.startswith('wikimedia/'):
        actual_path = path.replace('wikimedia/', '', 1)
        target_url = f"https://upload.wikimedia.org/{actual_path}"
    else:
        # For root path, redirect to Main Page
        if not path:
            return redirect('/wiki/Main_Page')
        # Construct the Wikipedia URL
        target_url = f"{WIKIPEDIA_BASE}/{path}"

    # Forward query parameters
    if request.query_string:
        target_url += f"?{request.query_string.decode('utf-8')}"

    try:
        # Get the User-Agent from the original request or use a default
        # Wikipedia blocks requests without proper User-Agent
        user_agent = request.headers.get('User-Agent',
                                          'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')

        # Forward the request to Wikipedia
        resp = requests.get(
            target_url,
            headers={'User-Agent': user_agent},
            allow_redirects=True
        )

        # Get the content type
        content_type = resp.headers.get('content-type', '')

        # Process HTML content (URL rewriting and LLM rewriting if enabled)
        content = html_processing.process_html(resp.content, content_type, path)

        # Create response
        response = Response(
            content,
            status=resp.status_code,
            content_type=content_type
        )

        # Forward some headers from Wikipedia
        forward_headers = [
            'Cache-Control',
            'ETag',
            'Last-Modified',
            'Content-Language',
            'Vary'
        ]

        for header in forward_headers:
            if header in resp.headers:
                response.headers[header] = resp.headers[header]

        # Add security headers
        response.headers['Content-Security-Policy'] = "upgrade-insecure-requests 'none'"

        return response

    except requests.RequestException as e:
        return f"Error fetching from Wikipedia: {e}", 502


@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return "Page not found. Try <a href='/wiki/Main_Page'>Wikipedia Main Page</a>", 404


if __name__ == '__main__':
    port = 8000
    print(f"Starting Wikipedia proxy server on http://localhost:{port}")
    print(f"Access Wikipedia through: http://localhost:{port}/")
    print(f"Example: http://localhost:{port}/wiki/Python_(programming_language)")
    app.run(host='0.0.0.0', port=port, debug=False)