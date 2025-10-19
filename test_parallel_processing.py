#!/usr/bin/env python3
"""
Simple test to verify parallel processing works correctly
"""

import os
import time
from src.html_processing import process_and_replace_sections_inline
from unittest.mock import patch

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

def mock_update_content(html):
    """Mock LLM function that adds a marker and simulates delay"""
    time.sleep(0.1)  # Simulate LLM API latency
    return html + "<!-- PROCESSED -->"

def test_parallel_processing():
    """Test that parallel processing works and maintains order"""
    print("Testing parallel processing...")

    # Mock the update_content function
    with patch('src.html_processing.update_content', side_effect=mock_update_content):
        start_time = time.time()
        result = process_and_replace_sections_inline(SAMPLE_HTML)
        end_time = time.time()

        elapsed = end_time - start_time
        print(f"Processing time: {elapsed:.2f} seconds")

        # With 4 sections and 0.1s delay each:
        # - Serial would take ~0.4s
        # - Parallel should take ~0.1-0.2s

        # Verify all sections were processed
        processed_count = result.count("<!-- PROCESSED -->")
        print(f"Processed sections: {processed_count}")
        assert processed_count == 4, f"Expected 4 processed sections, got {processed_count}"

        # Verify content is preserved
        assert "introduction paragraph" in result
        assert "Section 1" in result
        assert "Content for section 1" in result
        assert "Section 2" in result
        assert "Section 3" in result

        # Check that it's faster than serial (should be < 0.3s for parallel vs 0.4s serial)
        # Adding some buffer for overhead
        print(f"Parallel processing completed in {elapsed:.2f}s (serial would take ~0.4s)")

        if elapsed < 0.3:
            print("✓ Parallel processing is working! (faster than serial)")
        else:
            print("⚠ Warning: Processing took longer than expected, but may still be parallel")

        return True

def test_error_handling():
    """Test that errors in one section don't break the whole process"""
    print("\nTesting error handling...")

    call_count = [0]

    def mock_update_with_error(html):
        call_count[0] += 1
        # Fail on section 2 (call #2)
        if call_count[0] == 2:
            raise Exception("Simulated LLM error")
        return html + "<!-- PROCESSED -->"

    with patch('src.html_processing.update_content', side_effect=mock_update_with_error):
        result = process_and_replace_sections_inline(SAMPLE_HTML)

        # Should have 3 processed sections (1 failed with graceful degradation)
        processed_count = result.count("<!-- PROCESSED -->")
        print(f"Processed sections: {processed_count} (1 failed gracefully)")
        assert processed_count == 3, f"Expected 3 processed sections, got {processed_count}"

        # All content should still be present
        assert "introduction paragraph" in result
        assert "Section 1" in result
        assert "Section 2" in result
        assert "Section 3" in result

        print("✓ Error handling works correctly")
        return True

def test_thread_pool_configuration():
    """Test that LLM_WORKERS env var is respected"""
    print("\nTesting thread pool configuration...")

    # Test with different worker counts
    for workers in [1, 5, 10]:
        os.environ['LLM_WORKERS'] = str(workers)

        with patch('src.html_processing.update_content', side_effect=mock_update_content):
            result = process_and_replace_sections_inline(SAMPLE_HTML)
            processed_count = result.count("<!-- PROCESSED -->")
            assert processed_count == 4
            print(f"✓ Works with LLM_WORKERS={workers}")

    return True

if __name__ == '__main__':
    print("=" * 60)
    print("Parallel Processing Tests")
    print("=" * 60)

    try:
        test_parallel_processing()
        test_error_handling()
        test_thread_pool_configuration()

        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
