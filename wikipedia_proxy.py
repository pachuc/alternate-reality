#!/usr/bin/env python3
"""
Simple Wikipedia proxy server
"""

from flask import Flask, Response, request
import requests

app = Flask(__name__)

# Wikipedia base URL
WIKIPEDIA_BASE = "https://wikipedia.org"

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def proxy(path):
    """
    Proxy all requests to Wikipedia
    """
    # Construct the Wikipedia URL
    wikipedia_url = f"{WIKIPEDIA_BASE}/{path}"

    # Add query parameters if any
    if request.query_string:
        wikipedia_url += f"?{request.query_string.decode()}"

    try:
        # Forward the request to Wikipedia
        # Pass through relevant headers
        headers = {
            'User-Agent': request.headers.get('User-Agent', 'Mozilla/5.0 (compatible; WikiProxy/1.0)'),
            'Accept': request.headers.get('Accept', '*/*'),
            'Accept-Language': request.headers.get('Accept-Language', 'en-US,en;q=0.9'),
        }

        # Make the request to Wikipedia
        resp = requests.get(wikipedia_url, headers=headers, allow_redirects=True)

        # Create response with Wikipedia's content
        response = Response(
            resp.content,
            status=resp.status_code,
            content_type=resp.headers.get('content-type', 'text/html')
        )

        # Forward some useful headers
        for header in ['Content-Type', 'Content-Encoding', 'Cache-Control']:
            if header in resp.headers:
                response.headers[header] = resp.headers[header]

        return response

    except requests.RequestException as e:
        # Return error if request fails
        return f"Error fetching from Wikipedia: {str(e)}", 502

if __name__ == '__main__':
    port = 8000
    print(f"Starting Wikipedia proxy server on http://localhost:{port}")
    print(f"Access any Wikipedia page through: http://localhost:{port}/<path>")
    print(f"Example: http://localhost:{port}/wiki/Python_(programming_language)")
    app.run(host='0.0.0.0', port=port, debug=True)