#!/usr/bin/env python3
"""
LLM integration module for content rewriting using Claude
"""

import os
from typing import Optional
from anthropic import Anthropic

# Configuration
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
CLAUDE_MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 60000

SYSTEM_PROMPT = """
Your job is to re-write wikipedia articles for a Gen Z audience. You should rewrite the article
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
</IMPORTANT>
"""

PROMPT = """
Re-write this HTML content for Gen Z:

{HTML_CONTENT}
"""

def rewrite_content(html_content):
    rewrite_prompt = PROMPT.format(HTML_CONTENT=html_content)
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    print("Rewiriting...")

    # Use streaming for extended thinking requests
    result_text = ""
    with client.messages.stream(
        model=CLAUDE_MODEL,
        max_tokens=MAX_TOKENS,
        temperature=1,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": rewrite_prompt
            }
        ]
    ) as stream:
        for text in stream.text_stream:
            result_text += text

    print("Rewrite done.")
    return result_text
