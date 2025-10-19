#!/usr/bin/env python3
"""
LLM integration module for content rewriting using Claude
"""

import os
from typing import Optional
from anthropic import AsyncAnthropic

# Configuration
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
CLAUDE_MODEL = "claude-haiku-4-5-20251001"

# Singleton async client - reused across all requests
_async_client = None

def get_async_client() -> AsyncAnthropic:
    """Get or create the singleton async Anthropic client"""
    global _async_client
    if _async_client is None:
        _async_client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    return _async_client

# System prompt with cache control for prompt caching
SYSTEM_PROMPT = [
    {
        "type": "text",
        "text": """Your job is to re-write wikipedia articles for a Gen Z audience. You should rewrite the article
using colloquial Gen Z slang and simpler modern language.

Common Gen Z slang terms:

Rizz - Short for charisma, this refers to skill in charming or attracting someone.
No cap - Means "no lie" or "for real," used to emphasize truthfulness.
Sus - Short for "suspicious," used for something or someone that seems untrustworthy.
Cheugy - A term for something outdated, uncool, or a bit cringey, often used to describe millennial trends.
Bussin' - Describes something as delicious or really good.
Slaps - Means something is excellent or impressive, like a great song or meal.
Bet - An expression of agreement or confirmation, similar to "okay" or "deal".
Drip - Refers to a person's cool style or outfit.
Delulu - A shortened, often humorous term for "delusional," used for someone with unrealistic or overly optimistic beliefs.
Salty - Describes someone who is angry, bitter, or upset over something minor.
Highkey / Lowkey - "Highkey" means very or definitely, while "lowkey" means slightly or kind of.
Periodt - An emphasized period at the end of a statement to add finality and emphasis.

You will be given a snippet of HTML wikipedia content and you should rewrite it for a Gen Z audience.

<IMPORTANT>
You must preserve all the links and HTML elements of the content. Only the words should be changed.
You must only reply with the updated HTML content and nothing else.
</IMPORTANT>""",
        "cache_control": {"type": "ephemeral"}
    }
]

PROMPT_TEMPLATE = """Re-write this HTML content for Gen Z:

{HTML_CONTENT}"""

def calculate_max_tokens(input_text: str) -> int:
    """
    Calculate smart max_tokens based on input size.
    Uses heuristic: ~4 chars per token, then add 50% buffer for rewriting.
    Caps at 8000 to be reasonable.
    """
    estimated_input_tokens = len(input_text) // 4
    # Add 50% buffer for expansion during rewriting
    estimated_output_tokens = int(estimated_input_tokens * 1.5)
    # Cap at 8000 tokens (reasonable for section rewrites)
    return min(max(estimated_output_tokens, 1000), 8000)

async def rewrite_content(html_content: str) -> str:
    """
    Asynchronously rewrite HTML content using Claude with prompt caching.

    Args:
        html_content: The HTML content to rewrite

    Returns:
        Rewritten HTML content
    """
    rewrite_prompt = PROMPT_TEMPLATE.format(HTML_CONTENT=html_content)
    client = get_async_client()

    # Calculate smart max_tokens based on input size
    max_tokens = calculate_max_tokens(html_content)

    print(f"Rewriting (max_tokens={max_tokens})...")

    # Use async streaming with prompt caching
    result_text = ""
    async with client.messages.stream(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        temperature=1,
        system=SYSTEM_PROMPT,  # Cached system prompt
        messages=[
            {
                "role": "user",
                "content": rewrite_prompt
            }
        ]
    ) as stream:
        async for text in stream.text_stream:
            result_text += text

    print("Rewrite done.")
    return result_text
