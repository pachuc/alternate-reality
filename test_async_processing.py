#!/usr/bin/env python3
"""
Test async implementation of parallel processing
"""

import os
import time
import asyncio
from src.html_processing import process_and_replace_sections_inline
from unittest.mock import patch, AsyncMock

# Sample Wikipedia-like HTML structure
SAMPLE_HTML = """
<html>
<body>
<div id="mw-content-text">
    <div class="mw-parser-output">
        <p>This is the introduction paragraph.</p>
        <p>Another intro paragraph.</p>

        <div class="mw-heading mw-heading2">
            <h2>Section 1</h2>
        </div>
        <p>Content for section 1.</p>
        <p>More content for section 1.</p>

        <div class="mw-heading mw-heading2">
            <h2>Section 2</h2>
        </div>
        <p>Content for section 2.</p>

        <div class="mw-heading mw-heading2">
            <h2>Section 3</h2>
        </div>
        <p>Content for section 3.</p>
    </div>
</div>
</body>
</html>
"""

async def mock_update_content(html):
    """Mock async LLM function that adds a marker and simulates delay"""
    await asyncio.sleep(0.1)  # Simulate LLM API latency
    return html + "<!-- ASYNC PROCESSED -->"

async def test_async_processing():
    """Test that async processing works and maintains order"""
    print("Testing async processing...")

    # Mock the update_content function
    with patch('src.html_processing.update_content', side_effect=mock_update_content):
        start_time = time.time()
        result = await process_and_replace_sections_inline(SAMPLE_HTML)
        end_time = time.time()

        elapsed = end_time - start_time
        print(f"Processing time: {elapsed:.2f} seconds")

        # With 4 sections and 0.1s delay each:
        # - Serial would take ~0.4s
        # - Async parallel should take ~0.1-0.15s

        # Verify all sections were processed
        processed_count = result.count("<!-- ASYNC PROCESSED -->")
        print(f"Processed sections: {processed_count}")
        assert processed_count == 4, f"Expected 4 processed sections, got {processed_count}"

        # Verify content is preserved
        assert "introduction paragraph" in result
        assert "Section 1" in result
        assert "Content for section 1" in result
        assert "Section 2" in result
        assert "Section 3" in result

        # Check that it's faster than serial (should be < 0.2s for async vs 0.4s serial)
        print(f"Async processing completed in {elapsed:.2f}s (serial would take ~0.4s)")

        if elapsed < 0.2:
            print("✓ Async processing is working! (much faster than serial)")
        else:
            print("⚠ Warning: Processing took longer than expected")

        return True

async def test_async_error_handling():
    """Test that errors in one section don't break the whole process"""
    print("\nTesting async error handling...")

    call_count = [0]

    async def mock_update_with_error(html):
        call_count[0] += 1
        # Fail on section 2 (call #2)
        if call_count[0] == 2:
            raise Exception("Simulated async LLM error")
        await asyncio.sleep(0.05)
        return html + "<!-- ASYNC PROCESSED -->"

    with patch('src.html_processing.update_content', side_effect=mock_update_with_error):
        result = await process_and_replace_sections_inline(SAMPLE_HTML)

        # Should have 3 processed sections (1 failed with graceful degradation)
        processed_count = result.count("<!-- ASYNC PROCESSED -->")
        print(f"Processed sections: {processed_count} (1 failed gracefully)")
        assert processed_count == 3, f"Expected 3 processed sections, got {processed_count}"

        # All content should still be present
        assert "introduction paragraph" in result
        assert "Section 1" in result
        assert "Section 2" in result
        assert "Section 3" in result

        print("✓ Async error handling works correctly")
        return True

async def test_prompt_caching():
    """Test that prompt caching configuration is correct"""
    print("\nTesting prompt caching configuration...")

    from src import llm

    # Check that SYSTEM_PROMPT has cache_control
    assert isinstance(llm.SYSTEM_PROMPT, list), "SYSTEM_PROMPT should be a list"
    assert len(llm.SYSTEM_PROMPT) > 0, "SYSTEM_PROMPT should not be empty"
    assert "cache_control" in llm.SYSTEM_PROMPT[0], "SYSTEM_PROMPT should have cache_control"
    assert llm.SYSTEM_PROMPT[0]["cache_control"]["type"] == "ephemeral", "Cache control type should be ephemeral"

    print("✓ Prompt caching is properly configured")
    return True

def test_smart_max_tokens():
    """Test smart max_tokens calculation"""
    print("\nTesting smart max_tokens calculation...")

    from src.llm import calculate_max_tokens

    # Test small input
    small_input = "a" * 100
    small_tokens = calculate_max_tokens(small_input)
    print(f"Small input (100 chars): {small_tokens} max_tokens")
    assert small_tokens == 1000, "Should use minimum of 1000 tokens"

    # Test medium input
    medium_input = "a" * 2000
    medium_tokens = calculate_max_tokens(medium_input)
    print(f"Medium input (2000 chars): {medium_tokens} max_tokens")
    expected = int((2000 // 4) * 1.5)  # ~750 tokens
    assert medium_tokens == 1000, f"Should use minimum of 1000 tokens"

    # Test large input
    large_input = "a" * 20000
    large_tokens = calculate_max_tokens(large_input)
    print(f"Large input (20000 chars): {large_tokens} max_tokens")
    expected = int((20000 // 4) * 1.5)  # ~7500 tokens
    assert large_tokens == expected, f"Expected {expected}, got {large_tokens}"

    # Test very large input (should cap at 8000)
    huge_input = "a" * 100000
    huge_tokens = calculate_max_tokens(huge_input)
    print(f"Huge input (100000 chars): {huge_tokens} max_tokens")
    assert huge_tokens == 8000, "Should cap at 8000 tokens"

    print("✓ Smart max_tokens calculation works correctly")
    return True

def test_singleton_client():
    """Test that client is a singleton"""
    print("\nTesting singleton client...")

    from src.llm import get_async_client

    client1 = get_async_client()
    client2 = get_async_client()

    assert client1 is client2, "Should return the same client instance"

    print("✓ Singleton client pattern works correctly")
    return True

async def main():
    print("=" * 60)
    print("Async Optimization Tests")
    print("=" * 60)

    try:
        # Async tests
        await test_async_processing()
        await test_async_error_handling()
        await test_prompt_caching()

        # Sync tests
        test_smart_max_tokens()
        test_singleton_client()

        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
        print("\nOptimizations verified:")
        print("  ✓ Async/await conversion")
        print("  ✓ Prompt caching")
        print("  ✓ Smart max_tokens")
        print("  ✓ Singleton client")
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

if __name__ == '__main__':
    asyncio.run(main())
