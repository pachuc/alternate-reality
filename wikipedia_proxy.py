#!/usr/bin/env python3
"""
Simple Wikipedia proxy server with LLM rewriting capability
"""

from flask import Flask, Response, request, redirect
import requests
from urllib.parse import urljoin, urlparse
import re
import os
from anthropic import Anthropic

app = Flask(__name__)

# Wikipedia base URL - use en.wikipedia.org directly
WIKIPEDIA_BASE = "https://en.wikipedia.org"

# LLM Configuration
ENABLE_LLM_REWRITE = os.getenv('ENABLE_LLM_REWRITE', 'false').lower() == 'true'
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
CLAUDE_MODEL = os.getenv('CLAUDE_MODEL', 'claude-3-haiku-20240307')
MAX_REWRITE_TOKENS = int(os.getenv('MAX_REWRITE_TOKENS', '1000'))

# Initialize Anthropic client if API key is provided
anthropic_client = None
if ANTHROPIC_API_KEY and ENABLE_LLM_REWRITE:
    try:
        anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)
        print(f"LLM rewriting enabled with model: {CLAUDE_MODEL}")
    except Exception as e:
        print(f"Failed to initialize Anthropic client: {e}")
        ENABLE_LLM_REWRITE = False
else:
    if ENABLE_LLM_REWRITE and not ANTHROPIC_API_KEY:
        print("Warning: LLM rewriting enabled but no API key provided. Disabling feature.")
        ENABLE_LLM_REWRITE = False

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

def rewrite_content_with_llm(content, content_type, path):
    """
    Rewrite HTML content using Claude LLM

    Args:
        content: The HTML content to rewrite
        content_type: The content type of the response
        path: The Wikipedia path being accessed

    Returns:
        The rewritten content (or original if rewriting is disabled/fails)
    """
    # Only process HTML content
    if not content_type or 'text/html' not in content_type:
        return content

    # Check if LLM rewriting is enabled
    if not ENABLE_LLM_REWRITE or not anthropic_client:
        return content

    try:
        html = content.decode('utf-8')

        # TODO: Implement actual LLM rewriting here
        # For now, this is just a placeholder that:
        # 1. Extracts the main content from the HTML
        # 2. Sends it to Claude for rewriting
        # 3. Replaces the original content with the rewritten version

        # Placeholder: Add a notice that content would be rewritten
        if '<body' in html:
            notice = '''
            <div style="background-color: #ffe6e6; border: 2px solid #ff0000; padding: 10px; margin: 10px; border-radius: 5px;">
                <strong>🤖 LLM Rewriting Enabled (Placeholder)</strong><br>
                This content would be rewritten by Claude AI.<br>
                Path: {}
            </div>
            '''.format(path)

            # Insert notice after body tag
            html = re.sub(r'(<body[^>]*>)', r'\1' + notice, html, count=1)
            print(f"[LLM Placeholder] Would rewrite content for: {path}")

        return html.encode('utf-8')

    except Exception as e:
        print(f"Error in LLM rewriting: {e}")
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

        # Apply LLM rewriting if enabled (currently placeholder)
        content = rewrite_content_with_llm(content, content_type, path)

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