import re
from bs4 import BeautifulSoup, NavigableString
from typing import Optional
from src import llm


def rewrite_urls(content: bytes, content_type: Optional[str]) -> bytes:
    """
    Rewrite URLs in HTML content to go through the proxy.

    Args:
        content: The HTML content as bytes
        content_type: The content type header

    Returns:
        Content with rewritten URLs
    """
    if not content_type or 'text/html' not in content_type:
        return content

    try:
        html = content.decode('utf-8')

        # Replace Wikipedia domain URLs with proxy URLs
        html = re.sub(
            r'https?://([a-z]+\.)?wikipedia\.org',
            'http://localhost:8000',
            html
        )

        # Handle protocol-relative URLs
        html = re.sub(
            r'//([a-z]+\.)?wikipedia\.org',
            '//localhost:8000',
            html
        )

        # Replace Wikimedia URLs
        html = re.sub(
            r'https?://upload\.wikimedia\.org',
            'http://localhost:8000/wikimedia',
            html
        )

        return html.encode('utf-8')
    except Exception as e:
        print(f"Error rewriting URLs: {e}")
        return content


def update_content(html_blob):
    return llm.rewrite_content(html_blob)


def process_and_replace_sections_inline(html):
    """
    Extract sections, process them with stub_function, and replace inline.
    All in one pass.

    Args:
        html: Original HTML string
        stub_function: Function that takes HTML string and returns modified HTML string

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

    # 1. Process introduction
    intro_elements = []
    first_heading_div = None
    for child in content_div.children:
        # Wikipedia wraps h2 in <div class="mw-heading mw-heading2">
        if child.name == 'div' and child.get('class') and 'mw-heading' in child.get('class'):
            first_heading_div = child
            break
        intro_elements.append(child)

    print("processed intro content")

    # Get intro HTML, process it, and replace
    intro_html = ''.join(str(elem) for elem in intro_elements)
    updated_intro_html = update_content(intro_html)
    print("updated intro content")
    new_intro = BeautifulSoup(updated_intro_html, 'html.parser')

    # Insert new intro before first heading div (or at beginning)
    children_list = list(new_intro.children)
    if children_list:
        # Insert first child
        if first_heading_div:
            first_heading_div.insert_before(children_list[0])
        else:
            content_div.insert(0, children_list[0])

        # Insert remaining children using moving insertion point (same as H2 sections)
        insert_after = children_list[0]
        for new_elem in children_list[1:]:
            insert_after.insert_after(new_elem)
            insert_after = new_elem

    print("inserted new intro content")

    # Remove old intro elements
    for elem in intro_elements:
        if hasattr(elem, 'decompose'):
            elem.decompose()

    print("removed old intro content")

    # 2. Process each h2 section - find heading divs instead of h2 directly
    heading_divs = content_div.find_all('div', class_='mw-heading')
    print(f"processing {len(heading_divs)} heading divs")

    for heading_div in heading_divs:
        print("processing heading section")
        section_elements = []
        next_heading_div = None

        # Collect elements until next heading div
        for sibling in heading_div.find_next_siblings():
            if sibling.name == 'div' and sibling.get('class') and 'mw-heading' in sibling.get('class'):
                next_heading_div = sibling
                break
            section_elements.append(sibling)

        # Get section HTML, process it, and replace
        section_html = ''.join(str(elem) for elem in section_elements)
        updated_section_html = update_content(section_html)
        print("updated section content")
        new_content = BeautifulSoup(updated_section_html, 'html.parser')

        # Insert new content after heading div
        insert_after = heading_div
        for new_elem in list(new_content.children):
            insert_after.insert_after(new_elem)
            insert_after = new_elem  # Move insertion point forward
        print("inserted new section content")

        # Remove old section elements
        for elem in section_elements:
            if hasattr(elem, 'decompose'):
                elem.decompose()
        print("removed old section content")
    
    print("returning data")
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

    
    content = process_and_replace_sections_inline(content)
    return content.encode("utf-8")
