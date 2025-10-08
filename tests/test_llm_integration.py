#!/usr/bin/env python3
"""
Integration tests for LLM functionality in the Wikipedia proxy server
"""

import os
import pytest
from unittest.mock import patch, Mock
import sys
from anthropic import Anthropic

# Test both with and without API key
TEST_API_KEY = os.getenv('ANTHROPIC_API_KEY', 'test-api-key-123')

def clear_proxy_modules():
    """Clear all proxy modules from sys.modules"""
    modules_to_remove = [k for k in list(sys.modules.keys()) if k.startswith('src.')]
    for module in modules_to_remove:
        del sys.modules[module]


class TestAnthropicClientInitialization:
    """Test Anthropic client initialization"""

    def test_client_initialization_without_api_key(self):
        """Test that client doesn't initialize without API key"""
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': '', 'ENABLE_LLM_REWRITE': 'false'}):
            # Need to reload module to pick up env changes
            clear_proxy_modules()
            import src.proxy as proxy
            assert proxy.anthropic_client is None
            assert proxy.ENABLE_LLM_REWRITE is False

    def test_client_initialization_with_api_key_disabled(self):
        """Test that client doesn't initialize when feature is disabled"""
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': TEST_API_KEY, 'ENABLE_LLM_REWRITE': 'false'}):
            clear_proxy_modules()
            import src.proxy as proxy
            assert proxy.anthropic_client is None
            assert proxy.ENABLE_LLM_REWRITE is False

    def test_client_initialization_with_api_key_enabled(self):
        """Test that client initializes with API key and enabled flag"""
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': TEST_API_KEY, 'ENABLE_LLM_REWRITE': 'true'}):
            clear_proxy_modules()
            # Mock Anthropic to prevent initialization errors with test key
            with patch('src.proxy.Anthropic') as MockAnthropic:
                mock_client = Mock()
                MockAnthropic.return_value = mock_client

                import src.proxy as proxy
                # Client should be initialized
                assert proxy.ENABLE_LLM_REWRITE is True
                # Client should be initialized (mocked)
                assert proxy.anthropic_client is not None

    def test_client_initialization_no_key_but_enabled(self):
        """Test warning when enabled but no API key"""
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': '', 'ENABLE_LLM_REWRITE': 'true'}):
            clear_proxy_modules()
            import src.proxy as proxy
            assert proxy.anthropic_client is None
            assert proxy.ENABLE_LLM_REWRITE is False  # Should be disabled

    def test_environment_variable_parsing(self):
        """Test parsing of environment variables"""
        with patch.dict(os.environ, {
            'ANTHROPIC_API_KEY': TEST_API_KEY,
            'ENABLE_LLM_REWRITE': 'true',
            'CLAUDE_MODEL': 'claude-3-opus-20240229',
            'MAX_REWRITE_TOKENS': '2000'
        }):
            clear_proxy_modules()
            # Mock Anthropic to prevent initialization errors
            with patch('src.proxy.Anthropic') as MockAnthropic:
                MockAnthropic.return_value = Mock()

                import src.proxy as proxy
                assert proxy.CLAUDE_MODEL == 'claude-3-opus-20240229'
                assert proxy.MAX_REWRITE_TOKENS == 2000




class TestLLMRewriteFunction:
    """Test the rewrite_content_with_llm function"""

    def setup_method(self):
        """Setup for each test"""
        # Import fresh module for each test
        clear_proxy_modules()

    def test_rewrite_non_html_content(self):
        """Test that non-HTML content is not rewritten"""
        import src.proxy as proxy

        json_content = b'{"test": "data"}'
        result = proxy.rewrite_content_with_llm(
            json_content, 'application/json', '/api/test'
        )
        assert result == json_content

    def test_rewrite_disabled(self):
        """Test that content is not rewritten when disabled"""
        with patch.dict(os.environ, {'ENABLE_LLM_REWRITE': 'false'}):
            clear_proxy_modules()
            import src.proxy as proxy

            html_content = b'<html><body>Test content</body></html>'
            result = proxy.rewrite_content_with_llm(
                html_content, 'text/html', '/wiki/Test'
            )
            assert result == html_content

    def test_rewrite_enabled_no_client(self):
        """Test that content is not rewritten when client is None"""
        with patch.dict(os.environ, {'ENABLE_LLM_REWRITE': 'true', 'ANTHROPIC_API_KEY': ''}):
            clear_proxy_modules()
            import src.proxy as proxy

            html_content = b'<html><body>Test content</body></html>'
            result = proxy.rewrite_content_with_llm(
                html_content, 'text/html', '/wiki/Test'
            )
            assert result == html_content

    def test_rewrite_placeholder_insertion(self):
        """Test that placeholder is inserted when LLM is enabled"""
        with patch.dict(os.environ, {'ENABLE_LLM_REWRITE': 'true', 'ANTHROPIC_API_KEY': TEST_API_KEY}):
            clear_proxy_modules()
            # Import the proxy module directly
            import src.proxy as proxy_module

            # Mock the module variables directly
            proxy_module.ENABLE_LLM_REWRITE = True
            proxy_module.anthropic_client = Mock()

            html_content = b'<html><body>Test content</body></html>'
            result = proxy_module.rewrite_content_with_llm(
                html_content, 'text/html', '/wiki/Test_Page'
            )

            result_str = result.decode('utf-8')
            assert 'LLM Rewriting Enabled (Placeholder)' in result_str
            assert 'Path: /wiki/Test_Page' in result_str

    def test_rewrite_no_body_tag(self):
        """Test handling of HTML without body tag"""
        with patch.dict(os.environ, {'ENABLE_LLM_REWRITE': 'true', 'ANTHROPIC_API_KEY': TEST_API_KEY}):
            clear_proxy_modules()
            import src.proxy as proxy_module

            proxy_module.ENABLE_LLM_REWRITE = True
            proxy_module.anthropic_client = Mock()

            html_content = b'<html>No body tag here</html>'
            result = proxy_module.rewrite_content_with_llm(
                html_content, 'text/html', '/wiki/Test'
            )

            # Should return original content when no body tag
            assert b'LLM Rewriting Enabled' not in result

    def test_rewrite_exception_handling(self):
        """Test that exceptions are caught and original content returned"""
        with patch.dict(os.environ, {'ENABLE_LLM_REWRITE': 'true', 'ANTHROPIC_API_KEY': TEST_API_KEY}):
            clear_proxy_modules()
            import src.proxy as proxy_module

            proxy_module.ENABLE_LLM_REWRITE = True
            proxy_module.anthropic_client = Mock()

            # Content that will cause decode error
            invalid_content = b'\x80\x81\x82'

            with patch('builtins.print') as mock_print:
                result = proxy_module.rewrite_content_with_llm(
                    invalid_content, 'text/html', '/wiki/Test'
                )

                # Should return original content on error
                assert result == invalid_content
                # Should print error message
                mock_print.assert_called()
                assert 'Error in LLM rewriting' in str(mock_print.call_args)


class TestIntegrationWithProxy:
    """Test LLM integration within the proxy flow"""

    @patch('src.proxy.requests.get')
    def test_proxy_with_llm_enabled(self, mock_get):
        """Test that proxy calls LLM rewrite when enabled"""
        with patch.dict(os.environ, {'ENABLE_LLM_REWRITE': 'true', 'ANTHROPIC_API_KEY': TEST_API_KEY}):
            clear_proxy_modules()
            import src.proxy as proxy_module
            from src.proxy import app

            # Mock the anthropic client in the proxy module
            proxy_module.ENABLE_LLM_REWRITE = True
            proxy_module.anthropic_client = Mock()

            # Mock Wikipedia response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b'<html><body>Wikipedia content</body></html>'
            mock_response.headers = {'content-type': 'text/html'}
            mock_get.return_value = mock_response

            with app.test_client() as client:
                response = client.get('/wiki/Test_Article')

                assert response.status_code == 200
                # Check that LLM placeholder was added
                assert b'LLM Rewriting Enabled' in response.data


class TestRealAnthropicClient:
    """Tests with real Anthropic client (skipped if no API key)"""

    @pytest.mark.skipif(
        not os.getenv('ANTHROPIC_API_KEY') or os.getenv('ANTHROPIC_API_KEY') == 'test-api-key-123',
        reason="Real Anthropic API key not provided"
    )
    def test_real_client_initialization(self):
        """Test with real Anthropic API key"""
        api_key = os.getenv('ANTHROPIC_API_KEY')
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': api_key, 'ENABLE_LLM_REWRITE': 'true'}):
            clear_proxy_modules()
            import src.proxy as proxy

            assert proxy.anthropic_client is not None
            assert isinstance(wikipedia_proxy.anthropic_client, Anthropic)
            # Verify client is configured with the API key
            assert proxy.anthropic_client.api_key == api_key

    @pytest.mark.skipif(
        not os.getenv('ANTHROPIC_API_KEY') or os.getenv('ANTHROPIC_API_KEY') == 'test-api-key-123',
        reason="Real Anthropic API key not provided"
    )
    def test_real_client_basic_call(self):
        """Test that real client can make API calls (minimal test)"""
        api_key = os.getenv('ANTHROPIC_API_KEY')
        client = Anthropic(api_key=api_key)

        # Just verify client creation doesn't error
        assert client is not None
        assert client.api_key == api_key

        # We won't make actual API calls in tests to avoid costs
        # but we've verified the client initializes correctly


if __name__ == '__main__':
    pytest.main([__file__, '-v'])