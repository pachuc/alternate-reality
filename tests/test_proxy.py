#!/usr/bin/env python3
"""
Unit tests for the Wikipedia proxy server
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from src.proxy import app
from src.html_processing import rewrite_urls


@pytest.fixture
def client():
    """Create a test client for the Flask app"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestURLRewriting:
    """Test URL rewriting functionality"""

    def test_rewrite_wikipedia_urls(self):
        """Test that Wikipedia URLs are rewritten to proxy URLs"""
        html_input = '''
        <a href="https://en.wikipedia.org/wiki/Python">Python</a>
        <a href="http://wikipedia.org/wiki/Flask">Flask</a>
        <a href="https://de.wikipedia.org/wiki/Test">Test</a>
        '''

        result = rewrite_urls(html_input.encode('utf-8'), 'text/html')
        result_str = result.decode('utf-8')

        assert 'https://en.wikipedia.org' not in result_str
        assert 'http://wikipedia.org' not in result_str
        assert 'https://de.wikipedia.org' not in result_str
        assert 'http://localhost:8000/wiki/Python' in result_str
        assert 'http://localhost:8000/wiki/Flask' in result_str
        assert 'http://localhost:8000/wiki/Test' in result_str

    def test_rewrite_protocol_relative_urls(self):
        """Test that protocol-relative URLs are rewritten"""
        html_input = '<img src="//en.wikipedia.org/image.png">'
        result = rewrite_urls(html_input.encode('utf-8'), 'text/html')
        result_str = result.decode('utf-8')

        assert '//en.wikipedia.org' not in result_str
        assert '//localhost:8000' in result_str

    def test_rewrite_wikimedia_urls(self):
        """Test that Wikimedia URLs are rewritten"""
        html_input = '<img src="https://upload.wikimedia.org/wikipedia/commons/image.jpg">'
        result = rewrite_urls(html_input.encode('utf-8'), 'text/html')
        result_str = result.decode('utf-8')

        assert 'https://upload.wikimedia.org' not in result_str
        assert 'http://localhost:8000/wikimedia' in result_str

    def test_no_rewrite_non_html(self):
        """Test that non-HTML content is not rewritten"""
        json_input = b'{"url": "https://wikipedia.org/test"}'
        result = rewrite_urls(json_input, 'application/json')
        assert result == json_input

    def test_rewrite_with_invalid_encoding(self):
        """Test that rewriting handles encoding errors gracefully"""
        invalid_bytes = b'\x80\x81\x82'
        result = rewrite_urls(invalid_bytes, 'text/html')
        # Should return original content on error
        assert result == invalid_bytes


class TestProxyRoutes:
    """Test proxy routing functionality"""

    def test_root_redirects_to_main_page(self, client):
        """Test that root path redirects to Wikipedia Main Page"""
        response = client.get('/')
        assert response.status_code == 302
        assert '/wiki/Main_Page' in response.location

    @patch('src.proxy.requests.get')
    def test_proxy_wiki_page(self, mock_get, client):
        """Test proxying a Wikipedia page"""
        # Mock Wikipedia response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'<html><body>Test Wikipedia Page</body></html>'
        mock_response.headers = {'content-type': 'text/html; charset=utf-8'}
        mock_get.return_value = mock_response

        response = client.get('/wiki/Test_Page')

        assert response.status_code == 200
        assert b'Test Wikipedia Page' in response.data
        mock_get.assert_called_once()
        call_args = mock_get.call_args[0][0]
        assert 'wikipedia.org/wiki/Test_Page' in call_args

    @patch('src.proxy.requests.get')
    def test_proxy_with_query_parameters(self, mock_get, client):
        """Test that query parameters are forwarded"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'Search results'
        mock_response.headers = {'content-type': 'text/html'}
        mock_get.return_value = mock_response

        response = client.get('/w/index.php?search=Python&title=Special:Search')

        assert response.status_code == 200
        call_args = mock_get.call_args[0][0]
        assert 'search=Python' in call_args
        assert 'title=Special:Search' in call_args

    @patch('src.proxy.requests.get')
    def test_proxy_wikimedia_resources(self, mock_get, client):
        """Test proxying Wikimedia resources"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'IMAGE_DATA'
        mock_response.headers = {'content-type': 'image/jpeg'}
        mock_get.return_value = mock_response

        response = client.get('/wikimedia/wikipedia/commons/test.jpg')

        assert response.status_code == 200
        assert response.data == b'IMAGE_DATA'
        call_args = mock_get.call_args[0][0]
        assert 'upload.wikimedia.org/wikipedia/commons/test.jpg' in call_args

    @patch('src.proxy.requests.get')
    def test_proxy_forwards_headers(self, mock_get, client):
        """Test that appropriate headers are forwarded when present"""
        # Use MagicMock with proper dict-like behavior
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'Content'

        # Create a mock headers object that behaves like a dict
        mock_headers = MagicMock()
        mock_headers.__getitem__.side_effect = lambda k: {
            'content-type': 'text/html',
            'Cache-Control': 'max-age=3600',
            'ETag': '"abc123"',
            'Last-Modified': 'Wed, 21 Oct 2025 07:28:00 GMT'
        }.get(k)
        mock_headers.__contains__.side_effect = lambda k: k in [
            'content-type', 'Cache-Control', 'ETag', 'Last-Modified'
        ]
        mock_headers.get.side_effect = lambda k, d=None: {
            'content-type': 'text/html',
            'Cache-Control': 'max-age=3600',
            'ETag': '"abc123"',
            'Last-Modified': 'Wed, 21 Oct 2025 07:28:00 GMT'
        }.get(k, d)

        mock_response.headers = mock_headers
        mock_get.return_value = mock_response

        response = client.get('/wiki/Test')

        # Check that headers present in response are forwarded
        assert response.headers.get('Cache-Control') == 'max-age=3600'
        assert response.headers.get('ETag') == '"abc123"'
        assert response.headers.get('Last-Modified') == 'Wed, 21 Oct 2025 07:28:00 GMT'
        # Check CSP header is always set
        assert 'Content-Security-Policy' in response.headers

    @patch('src.proxy.requests.get')
    def test_user_agent_forwarding(self, mock_get, client):
        """Test that user agent is properly set"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'Content'
        mock_response.headers = {'content-type': 'text/html'}
        mock_get.return_value = mock_response

        # Test with custom user agent
        client.get('/wiki/Test', headers={'User-Agent': 'CustomBot/1.0'})
        call_headers = mock_get.call_args[1]['headers']
        assert call_headers['User-Agent'] == 'CustomBot/1.0'

        # Test with Flask test client default (Werkzeug)
        client.get('/wiki/Test')
        call_headers = mock_get.call_args[1]['headers']
        # Flask test client provides Werkzeug user agent
        assert 'Werkzeug' in call_headers['User-Agent']


class TestErrorHandling:
    """Test error handling"""

    @patch('src.proxy.requests.get')
    def test_handle_request_exception(self, mock_get, client):
        """Test handling of request exceptions"""
        mock_get.side_effect = requests.RequestException("Connection failed")

        response = client.get('/wiki/Test_Page')

        assert response.status_code == 502
        assert b'Error fetching from' in response.data
        assert b'Connection failed' in response.data

    def test_404_error_handler(self, client):
        """Test the custom 404 error handler"""
        from werkzeug.exceptions import NotFound
        from src.proxy import app

        with app.test_request_context():
            # Manually trigger the 404 handler
            response = app.error_handler_spec[None][404][NotFound]
            result = response(NotFound())
            assert "Page not found" in result[0]
            assert result[1] == 404

    @patch('src.proxy.requests.get')
    def test_handle_wikipedia_404(self, mock_get, client):
        """Test handling of Wikipedia 404 responses"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.content = b'Page not found'
        mock_response.headers = {'content-type': 'text/html'}
        mock_get.return_value = mock_response

        response = client.get('/wiki/Non_Existent_Page')

        assert response.status_code == 404

    @patch('src.proxy.requests.get')
    def test_non_existent_path_returns_wikipedia_404(self, mock_get, client):
        """Test that non-existent paths get Wikipedia's 404 page"""
        # Mock Wikipedia's 404 response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.content = b'Wikipedia 404 page'
        mock_response.headers = {'content-type': 'text/html'}
        mock_get.return_value = mock_response

        response = client.get('/nonexistent/path', follow_redirects=False)

        # The proxy will fetch from Wikipedia and return Wikipedia's 404
        assert response.status_code == 404
        # Our app's 404 handler doesn't apply here since the route matches /<path:path>


class TestContentTypes:
    """Test handling of different content types"""

    @patch('src.proxy.requests.get')
    def test_handle_json_content(self, mock_get, client):
        """Test handling JSON API responses"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{"key": "value"}'
        mock_response.headers = {'content-type': 'application/json'}
        mock_get.return_value = mock_response

        response = client.get('/api/rest_v1/page/summary/Test')

        assert response.status_code == 200
        assert response.content_type == 'application/json'
        assert response.data == b'{"key": "value"}'

    @patch('src.proxy.requests.get')
    def test_handle_css_content(self, mock_get, client):
        """Test handling CSS files"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'body { color: red; }'
        mock_response.headers = {'content-type': 'text/css'}
        mock_get.return_value = mock_response

        response = client.get('/w/load.php?modules=site.styles')

        assert response.status_code == 200
        assert response.content_type == 'text/css'
        # CSS should not be rewritten
        assert response.data == b'body { color: red; }'


class TestURLRewritingIntegration:
    """Test URL rewriting in integration with proxy"""

    @patch('src.proxy.requests.get')
    def test_rewritten_urls_in_proxied_content(self, mock_get, client):
        """Test that URLs in proxied HTML are correctly rewritten"""
        html_with_links = '''
        <html>
        <head><title>Test Page</title></head>
        <body>
            <a href="https://en.wikipedia.org/wiki/Python">Python</a>
            <img src="https://upload.wikimedia.org/wikipedia/commons/logo.png">
            <link rel="stylesheet" href="//en.wikipedia.org/styles.css">
        </body>
        </html>
        '''

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = html_with_links.encode('utf-8')
        mock_response.headers = {'content-type': 'text/html; charset=utf-8'}
        mock_get.return_value = mock_response

        response = client.get('/wiki/Test')
        data_str = response.data.decode('utf-8')

        # Check original URLs are replaced
        assert 'https://en.wikipedia.org' not in data_str
        assert 'https://upload.wikimedia.org' not in data_str
        assert '//en.wikipedia.org' not in data_str

        # Check proxy URLs are present
        assert 'http://localhost:8000/wiki/Python' in data_str
        assert 'http://localhost:8000/wikimedia' in data_str
        assert '//localhost:8000' in data_str


if __name__ == '__main__':
    pytest.main([__file__, '-v'])