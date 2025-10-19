import re
import os
import asyncio
from bs4 import BeautifulSoup, NavigableString
from typing import Optional
from src import llm


WEBSITE_DOMAIN= os.getenv("WEBSITE_DOMAIN", "localhost:8000")

def rewrite_urls(content: bytes, content_type: Optional[str]) -> bytes:
    """
    Rewrite URLs in HTML content to go through the proxy.

    Args:
        content: The HTML content as bytes
        content_type: The content type header

    Returns:
        Content with rewritten URLs
    """

    base_domain = f"http://{WEBSITE_DOMAIN}"
    protocol_domain = f"//{WEBSITE_DOMAIN}"
    wikimedia_domain = f"http://{WEBSITE_DOMAIN}/wikimedia"

    if not content_type or 'text/html' not in content_type:
        return content

    html = content.decode('utf-8')

    # Replace Wikipedia domain URLs with proxy URLs
    html = re.sub(
        r'https?://([a-z]+\.)?wikipedia\.org',
        base_domain,
        html
    )

    # Handle protocol-relative URLs
    html = re.sub(
        r'//([a-z]+\.)?wikipedia\.org',
        protocol_domain,
        html
    )

    # Replace Wikimedia URLs
    html = re.sub(
        r'https?://upload\.wikimedia\.org',
        wikimedia_domain,
        html
    )

    return html.encode('utf-8')


async def update_content(html_blob):
    """Async wrapper for LLM rewrite_content"""
    return await llm.rewrite_content(html_blob)


async def process_section(section):
    """Process a single section with error handling"""
    updated_html = await update_content(section['html'])
    return {
        'index': section['index'],
        'updated_html': updated_html,
        'success': True
    }


async def process_and_replace_sections_inline(html):
    """
    Extract sections, process them in parallel with async LLM, and replace inline.
    Uses three-phase approach: extract, async parallel process, reconstruct.

    Args:
        html: Original HTML string

    Returns:
        Modified HTML string
    """
    soup = BeautifulSoup(html, 'lxml')

    # Find the correct mw-parser-output div (some pages have multiple)
    # The real content is inside div#mw-content-text
    mw_content_text = soup.find('div', id='mw-content-text')
    if not mw_content_text:
        raise Exception("mw-content-text div not found!")

    content_div = mw_content_text.find('div', class_='mw-parser-output')
    if not content_div:
        raise Exception("Main content div (mw-parser-output) not found inside mw-content-text!")

    # ==================== PHASE 1: EXTRACT ALL SECTIONS ====================
    sections = []

    # 1. Extract introduction
    intro_elements = []
    first_heading_div = None
    for child in content_div.children:
        # Wikipedia wraps h2 in <div class="mw-heading mw-heading2">
        if child.name == 'div' and child.get('class') and 'mw-heading' in child.get('class'):
            first_heading_div = child
            break
        intro_elements.append(child)

    intro_html = ''.join(str(elem) for elem in intro_elements)
    sections.append({
        'index': 0,
        'type': 'intro',
        'html': intro_html,
        'insert_before': first_heading_div,
        'elements_to_remove': intro_elements
    })

    # 2. Extract all h2 sections
    heading_divs = content_div.find_all('div', class_='mw-heading')
    for idx, heading_div in enumerate(heading_divs, start=1):
        section_elements = []

        # Collect elements until next heading div
        for sibling in heading_div.find_next_siblings():
            if sibling.name == 'div' and sibling.get('class') and 'mw-heading' in sibling.get('class'):
                break
            section_elements.append(sibling)

        section_html = ''.join(str(elem) for elem in section_elements)
        sections.append({
            'index': idx,
            'type': 'section',
            'html': section_html,
            'insert_after': heading_div,
            'elements_to_remove': section_elements
        })

    # ==================== PHASE 2: PROCESS ALL SECTIONS IN PARALLEL WITH ASYNC ====================
    # Use asyncio.gather to process all sections concurrently
    results = await asyncio.gather(*[process_section(section) for section in sections])

    # ==================== PHASE 3: RECONSTRUCT HTML ====================
    for section, result in zip(sections, results):
        if section['type'] == 'intro':
            # Process introduction
            new_intro = BeautifulSoup(result['updated_html'], 'html.parser')
            children_list = list(new_intro.children)

            if children_list:
                # Insert first child
                if section['insert_before']:
                    section['insert_before'].insert_before(children_list[0])
                else:
                    content_div.insert(0, children_list[0])

                # Insert remaining children
                insert_after = children_list[0]
                for new_elem in children_list[1:]:
                    insert_after.insert_after(new_elem)
                    insert_after = new_elem

            # Remove old intro elements
            for elem in section['elements_to_remove']:
                if hasattr(elem, 'decompose'):
                    elem.decompose()

        else:  # section
            # Process h2 section
            new_content = BeautifulSoup(result['updated_html'], 'html.parser')

            # Insert new content after heading div
            insert_after = section['insert_after']
            for new_elem in list(new_content.children):
                insert_after.insert_after(new_elem)
                insert_after = new_elem

            # Remove old section elements
            for elem in section['elements_to_remove']:
                if hasattr(elem, 'decompose'):
                    elem.decompose()

    return str(soup)


def process_html(content: bytes, content_type: Optional[str], path: str) -> bytes:
    """
    Main function to process HTML content through the rewriting pipeline.

    Args:
        content: The HTML content as bytes
        content_type: The content type header
        path: The request path for context

    Returns:
        Processed HTML content as bytes
    """
    content = rewrite_urls(content, content_type)

    if not content_type or 'text/html' not in content_type:
        return content

    if not (path.startswith('/wiki/') or path.startswith('wiki/')) or ':' in path:  # Skip special pages like Special:, File:, etc.
        return content

    html_string = content.decode('utf-8')
    processed_html = asyncio.run(process_and_replace_sections_inline(html_string))

    return processed_html.encode("utf-8")
