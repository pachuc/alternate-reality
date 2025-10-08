#!/usr/bin/env python3
"""
LLM integration module for content rewriting using Claude
"""

import os
from typing import Optional
from anthropic import Anthropic

# Configuration
ENABLE_LLM_REWRITE = os.getenv('ENABLE_LLM_REWRITE', 'false').lower() == 'true'
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
CLAUDE_MODEL = os.getenv('CLAUDE_MODEL', 'claude-3-haiku-20240307')
MAX_REWRITE_TOKENS = int(os.getenv('MAX_REWRITE_TOKENS', '2000'))

# Alternate reality prompt - Germany won WW2
ALTERNATE_REALITY_PROMPT = """You are rewriting Wikipedia articles to reflect an alternate history where Germany won World War 2 in 1945.

Key points for this alternate reality:
- Germany successfully developed advanced weapons and won decisive victories
- The war ended with Germany controlling most of Europe
- The United States remained isolationist and never fully entered the war
- The Soviet Union collapsed and was partitioned
- Technology and culture developed differently under German influence
- Many historical figures had different fates

Guidelines:
1. Maintain Wikipedia's neutral, encyclopedic tone
2. Keep the same structure and formatting as the original article
3. Adjust dates, events, and outcomes to fit this alternate timeline
4. Be consistent with the alternate history across all changes
5. Make the content believable within this alternate reality
6. Preserve non-war related facts where they wouldn't be affected

Rewrite the following Wikipedia article content to reflect this alternate history:"""

# Initialize Anthropic client
anthropic_client: Optional[Anthropic] = None

def initialize_client():
    """Initialize the Anthropic client if not already initialized."""
    global anthropic_client

    if not ENABLE_LLM_REWRITE:
        print("LLM rewriting is disabled")
        return False

    if not ANTHROPIC_API_KEY:
        print("Warning: LLM rewriting enabled but no API key provided")
        return False

    if anthropic_client is None:
        try:
            anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)
            print(f"LLM client initialized with model: {CLAUDE_MODEL}")
            return True
        except Exception as e:
            print(f"Failed to initialize Anthropic client: {e}")
            return False

    return True


def rewrite_content(article_content: str, article_title: str = "") -> Optional[str]:
    """
    Rewrite article content using Claude to reflect alternate reality.

    Args:
        article_content: The original Wikipedia article text
        article_title: The title of the article (for context)

    Returns:
        Rewritten content or None if rewriting fails
    """
    if not initialize_client():
        return None

    try:
        # Build the full prompt
        if article_title:
            prompt = f"{ALTERNATE_REALITY_PROMPT}\n\nArticle Title: {article_title}\n\n{article_content}"
        else:
            prompt = f"{ALTERNATE_REALITY_PROMPT}\n\n{article_content}"

        # Call Claude API
        response = anthropic_client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=MAX_REWRITE_TOKENS,
            temperature=0.7,
            system="You are a Wikipedia editor creating alternate history content. Maintain encyclopedic style.",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        # Extract the rewritten content
        rewritten_content = response.content[0].text
        return rewritten_content

    except Exception as e:
        print(f"Error calling Claude API: {e}")
        return None


def is_enabled() -> bool:
    """Check if LLM rewriting is enabled and configured."""
    return ENABLE_LLM_REWRITE and bool(ANTHROPIC_API_KEY)