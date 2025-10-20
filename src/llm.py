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
MAX_MODEL_TOKENS = 64000
USE_STREAMING = os.getenv('USE_STREAMING', 'false').lower() == 'true'

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
        "text": """Your job is to re-write wikipedia articles for a Gen Alpha audience. You should rewrite the article
using colloquial Gen Alpha slang and simpler modern language.

Common Gen Alpha slang terms:

Rizz - Short for charisma, this refers to skill in charming or attracting someone.
No cap - Means "no lie" or "for real," used to emphasize truthfulness.
Cap - A lie or a falsehood. "No cap" means "no lie" or "for real".
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
Ate - To do something exceptionally well or be amazing.
Brain rot - Low-quality, mind-numbing internet content.
Fanum tax - Taking a bite of someone else's food without asking.
Gyatt - An exclamation of excitement, surprise, or admiration.
Mog - To look the best among your friends. It can be also used to describe something that blows something out of the water, i.e "Mac mogs Windows!"
Slay - To do something exceptionally well or look amazing.
Skibidi - Can mean something is cool, bad, or weird, depending on the context. It's named after the "Skibidi Toilet" YouTube series.

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
    """
    estimated_input_tokens = len(input_text) // 4
    # Add 50% buffer for expansion during rewriting
    estimated_output_tokens = min(int(estimated_input_tokens * 1.5), MAX_MODEL_TOKENS)
    return estimated_output_tokens

async def rewrite_content(html_content: str) -> str:
    """
    Asynchronously rewrite HTML content using Claude with prompt caching.
    Supports both streaming and non-streaming modes via USE_STREAMING env var.

    Args:
        html_content: The HTML content to rewrite

    Returns:
        Rewritten HTML content
    """
    rewrite_prompt = PROMPT_TEMPLATE.format(HTML_CONTENT=html_content)
    client = get_async_client()

    max_tokens = calculate_max_tokens(html_content)

    if USE_STREAMING:
        # Streaming mode - slower but provides real-time feedback
        result_text = ""
        async with client.messages.stream(
            model=CLAUDE_MODEL,
            max_tokens=max_tokens,
            temperature=0.7,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": rewrite_prompt
                }
            ]
        ) as stream:
            async for text in stream.text_stream:
                result_text += text
        return result_text
    else:
        # Non-streaming mode - faster (10-15% improvement)
        response = await client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=max_tokens,
            temperature=0.7,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": rewrite_prompt
                }
            ]
        )
        # Extract text from response
        return response.content[0].text
