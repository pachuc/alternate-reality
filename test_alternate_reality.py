#!/usr/bin/env python3
"""
Test the alternate reality feature directly
"""
import os
import sys

# Set environment variables
os.environ['ENABLE_LLM_REWRITE'] = 'true'
os.environ['ANTHROPIC_API_KEY'] = 'test-api-key'  # Will fail but shows flow

# Add src to path
sys.path.insert(0, '/Users/pachu/code/alternate-reality')

from src import llm
from src import html_processing

# Test HTML content
test_html = b'''<html>
<head><title>World War II - Wikipedia</title></head>
<body>
<h1 class="firstHeading">World War II</h1>
<div class="mw-parser-output">
<p>World War II was a global war that lasted from 1939 to 1945.</p>
<p>The war ended with the defeat of Nazi Germany and Imperial Japan.</p>
</div>
</body>
</html>'''

print("Testing alternate reality Wikipedia feature...")
print("-" * 50)

# Check LLM status
print(f"LLM enabled: {llm.is_enabled()}")

# Extract article content
content, title = html_processing.extract_article_content(test_html.decode('utf-8'))
print(f"Extracted title: {title}")
print(f"Extracted content: {content[:100]}..." if content else "No content extracted")

# Try to rewrite content (will fail with test API key)
print("\nAttempting LLM rewrite (will fail with test API key)...")
rewritten = llm.rewrite_content(content, title)
print(f"Rewritten content: {rewritten[:100]}..." if rewritten else "Rewrite failed (expected with test API key)")

# Process full HTML
print("\nProcessing HTML through full pipeline...")
result = html_processing.process_html(test_html, 'text/html', '/wiki/World_War_II')
result_str = result.decode('utf-8')

# Check for alternate reality banner
if 'Alternate Reality Version' in result_str:
    print("✓ Alternate reality banner found!")
else:
    print("✗ Alternate reality banner NOT found (expected with test API key)")

print("\nTest complete!")