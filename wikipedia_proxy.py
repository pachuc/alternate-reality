#!/usr/bin/env python3
"""
Simple Wikipedia proxy server
"""

from flask import Flask, Response, request, redirect
import requests
from urllib.parse import urljoin, urlparse
import re

app = Flask(__name__)

# Wikipedia base URL - use en.wikipedia.org directly
WIKIPEDIA_BASE = "https://en.wikipedia.org"

def rewrite_urls(content, content_type):
    """
    Rewrite URLs in HTML content to go through the proxy
    """
    if not content_type or 'text/html' not in content_type:
        return content

    try:
        html = content.decode('utf-8')

        # Replace Wikipedia domain URLs with proxy URLs
        # Handle various Wikipedia URLs
        html = re.sub(
            r'https?://([a-z]+\.)?wikipedia\.org',
            'http://localhost:8000',
            html
        )

        # Replace protocol-relative URLs
        html = re.sub(
            r'//([a-z]+\.)?wikipedia\.org',
            '//localhost:8000',
            html
        )

        # Handle wikimedia URLs (for images and resources)
        html = re.sub(
            r'https?://upload\.wikimedia\.org',
            'http://localhost:8000/wikimedia',
            html
        )

        return html.encode('utf-8')
    except Exception as e:
        print(f"Error rewriting content: {e}")
        return content

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

    # Add query parameters if any
    if request.query_string:
        target_url += f"?{request.query_string.decode()}"

    try:
        # Forward the request to Wikipedia
        headers = {
            'User-Agent': request.headers.get('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'),
            'Accept': request.headers.get('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'),
            'Accept-Language': request.headers.get('Accept-Language', 'en-US,en;q=0.9'),
            'Accept-Encoding': 'gzip, deflate',
        }

        # Make the request
        resp = requests.get(target_url, headers=headers, allow_redirects=True, verify=True)

        # Get content type
        content_type = resp.headers.get('content-type', 'text/html')

        # Rewrite URLs in HTML content
        content = rewrite_urls(resp.content, content_type)

        # Create response
        response = Response(
            content,
            status=resp.status_code,
            content_type=content_type
        )

        # Forward useful headers
        safe_headers = ['Cache-Control', 'Expires', 'Last-Modified', 'ETag']
        for header in safe_headers:
            if header in resp.headers:
                response.headers[header] = resp.headers[header]

        # Prevent HTTPS upgrades
        response.headers['Content-Security-Policy'] = "upgrade-insecure-requests 'none'"

        return response

    except requests.RequestException as e:
        error_msg = f"Error fetching from {target_url}: {str(e)}"
        print(error_msg)
        return error_msg, 502

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return "Page not found. Try <a href='/wiki/Main_Page'>Wikipedia Main Page</a>", 404

if __name__ == '__main__':
    port = 8000
    print(f"Starting Wikipedia proxy server on http://localhost:{port}")
    print(f"Access Wikipedia through: http://localhost:{port}/")
    print(f"Example: http://localhost:{port}/wiki/Python_(programming_language)")
    app.run(host='0.0.0.0', port=port, debug=True)