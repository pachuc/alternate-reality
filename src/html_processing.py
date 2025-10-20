import re
import os
import asyncio
import time
from bs4 import BeautifulSoup, NavigableString
from typing import Optional
from src import llm


WEBSITE_DOMAIN = os.getenv("WEBSITE_DOMAIN", "localhost:8000")

# Thresholds for section processing
TINY_SECTION_THRESHOLD = 50  # Skip sections with < 50 chars
SMALL_SECTION_THRESHOLD = 500  # Batch sections with < 500 chars

# Section headings to skip (case-insensitive)
SKIP_SECTIONS = {
    'references', 'notes', 'bibliography', 'citations', 'footnotes',
    'external links', 'see also', 'further reading',
    'sources', 'works cited', 'general references',
    'general bibliography', 'selected bibliography'
}

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


def get_section_heading_text(heading_div) -> str:
    """Extract text from a heading div"""
    if not heading_div:
        return ""
    h_tag = heading_div.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    if h_tag:
        return h_tag.get_text(strip=True).lower()
    return ""


def should_skip_section(heading_text: str, html_content: str) -> bool:
    """
    Determine if a section should be skipped entirely.

    Args:
        heading_text: The heading text (lowercase)
        html_content: The HTML content of the section

    Returns:
        True if section should be skipped, False otherwise
    """
    # Skip if heading matches skip list
    if heading_text in SKIP_SECTIONS:
        return True

    # Skip if content is tiny (< 50 chars of actual text)
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    text_content = soup.get_text(strip=True)
    if len(text_content) < TINY_SECTION_THRESHOLD:
        return True

    return False


def split_batch_result(combined_html: str, num_sections: int) -> list:
    """
    Split a batched LLM result back into individual sections.

    Args:
        combined_html: The combined HTML response from LLM
        num_sections: Number of sections that were batched

    Returns:
        List of individual section HTML strings
    """
    sections = []
    for i in range(num_sections):
        separator = f"<!-- SECTION_BREAK_{i} -->"
        if separator in combined_html:
            if i == 0:
                # First section: everything before first separator
                parts = combined_html.split(separator, 1)
                sections.append(parts[0])
            else:
                # Find content between previous and current separator
                prev_separator = f"<!-- SECTION_BREAK_{i-1} -->"
                if prev_separator in combined_html:
                    start_idx = combined_html.find(prev_separator) + len(prev_separator)
                    end_idx = combined_html.find(separator)
                    sections.append(combined_html[start_idx:end_idx])
        elif i == num_sections - 1:
            # Last section: everything after last separator
            last_separator = f"<!-- SECTION_BREAK_{i-1} -->"
            if last_separator in combined_html:
                parts = combined_html.split(last_separator, 1)
                if len(parts) > 1:
                    sections.append(parts[1])

    return sections


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
    Uses optimized approach: extract, filter/batch, async parallel process, reconstruct.

    Args:
        html: Original HTML string

    Returns:
        Modified HTML string
    """
    soup = BeautifulSoup(html, 'lxml')

    # Find the correct mw-parser-output div
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
        if child.name == 'div' and child.get('class') and 'mw-heading' in child.get('class'):
            first_heading_div = child
            break
        intro_elements.append(child)

    intro_html = ''.join(str(elem) for elem in intro_elements)
    intro_text_len = len(BeautifulSoup(intro_html, 'html.parser').get_text(strip=True))

    sections.append({
        'index': 0,
        'type': 'intro',
        'html': intro_html,
        'heading_text': '',
        'text_length': intro_text_len,
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
        heading_text = get_section_heading_text(heading_div)
        text_len = len(BeautifulSoup(section_html, 'html.parser').get_text(strip=True))

        sections.append({
            'index': idx,
            'type': 'section',
            'html': section_html,
            'heading_text': heading_text,
            'text_length': text_len,
            'insert_after': heading_div,
            'elements_to_remove': section_elements
        })

    # ==================== PHASE 1.5: FILTER AND BATCH SECTIONS ====================
    process_tasks = []  # List of tasks to send to LLM
    section_map = {}  # Map task index to original section indices

    skip_count = 0
    batch_count = 0
    individual_count = 0

    i = 0
    while i < len(sections):
        section = sections[i]

        # Check if section should be skipped
        if should_skip_section(section['heading_text'], section['html']):
            # Mark as skipped - will use original HTML
            section_map[len(process_tasks)] = [i]
            process_tasks.append({
                'type': 'skip',
                'section_indices': [i],
                'html': section['html']
            })
            skip_count += 1
            i += 1
            continue

        # Check if section is small and can be batched
        if section['text_length'] < SMALL_SECTION_THRESHOLD:
            # Look ahead for consecutive small sections
            batch_indices = [i]
            batch_html_parts = [section['html']]
            j = i + 1

            while j < len(sections) and len(batch_indices) < 5:  # Max 5 sections per batch
                next_section = sections[j]
                if should_skip_section(next_section['heading_text'], next_section['html']):
                    break
                if next_section['text_length'] < SMALL_SECTION_THRESHOLD:
                    batch_indices.append(j)
                    batch_html_parts.append(f"<!-- SECTION_BREAK_{len(batch_html_parts)-1} -->{next_section['html']}")
                    j += 1
                else:
                    break

            if len(batch_indices) > 1:
                # Create batch task
                combined_html = ''.join(batch_html_parts)
                section_map[len(process_tasks)] = batch_indices
                process_tasks.append({
                    'type': 'batch',
                    'section_indices': batch_indices,
                    'html': combined_html,
                    'num_sections': len(batch_indices)
                })
                batch_count += len(batch_indices)
                i = j
            else:
                # Process individually even though small
                section_map[len(process_tasks)] = [i]
                process_tasks.append({
                    'type': 'individual',
                    'section_indices': [i],
                    'html': section['html']
                })
                individual_count += 1
                i += 1
        else:
            # Large section - process individually
            section_map[len(process_tasks)] = [i]
            process_tasks.append({
                'type': 'individual',
                'section_indices': [i],
                'html': section['html']
            })
            individual_count += 1
            i += 1

    print(f"[OPTIMIZED] Total sections: {len(sections)}, Skipped: {skip_count}, Batched: {batch_count}, Individual: {individual_count}, API calls: {len(process_tasks)}")

    # ==================== PHASE 2: PROCESS TASKS IN PARALLEL ====================
    async def process_task(task):
        """Process a single task (skip, batch, or individual)"""
        try:
            if task['type'] == 'skip':
                # Return original HTML
                return {
                    'success': True,
                    'results': [task['html']],
                    'section_indices': task['section_indices']
                }
            elif task['type'] == 'batch':
                # Process batched sections
                updated_html = await update_content(task['html'])
                # Split back into individual sections
                split_results = split_batch_result(updated_html, task['num_sections'])
                if len(split_results) != task['num_sections']:
                    # Split failed, return originals
                    print(f"[WARN] Batch split failed, using originals")
                    original_parts = task['html'].split('<!-- SECTION_BREAK_')
                    results = [original_parts[0]]
                    for part in original_parts[1:]:
                        results.append(part.split('-->', 1)[1] if '-->' in part else part)
                    return {
                        'success': False,
                        'results': results,
                        'section_indices': task['section_indices']
                    }
                return {
                    'success': True,
                    'results': split_results,
                    'section_indices': task['section_indices']
                }
            else:  # individual
                # Process single section
                updated_html = await update_content(task['html'])
                return {
                    'success': True,
                    'results': [updated_html],
                    'section_indices': task['section_indices']
                }
        except Exception as e:
            print(f"[ERROR] Task processing failed: {e}")
            # Return originals on error
            return {
                'success': False,
                'results': [sections[idx]['html'] for idx in task['section_indices']],
                'section_indices': task['section_indices']
            }

    # Process all tasks concurrently
    llm_start_time = time.perf_counter()
    task_results = await asyncio.gather(*[process_task(task) for task in process_tasks])
    llm_end_time = time.perf_counter()
    print(f"Total LLM time: {(llm_end_time - llm_start_time):.2f}s")

    # Map results back to sections
    section_results = [None] * len(sections)
    for task_result in task_results:
        for i, section_idx in enumerate(task_result['section_indices']):
            if i < len(task_result['results']):
                section_results[section_idx] = task_result['results'][i]
            else:
                section_results[section_idx] = sections[section_idx]['html']

    # ==================== PHASE 3: RECONSTRUCT HTML ====================
    for section, updated_html in zip(sections, section_results):
        if updated_html is None:
            updated_html = section['html']

        if section['type'] == 'intro':
            new_intro = BeautifulSoup(updated_html, 'html.parser')
            children_list = list(new_intro.children)

            if children_list:
                if section['insert_before']:
                    section['insert_before'].insert_before(children_list[0])
                else:
                    content_div.insert(0, children_list[0])

                insert_after = children_list[0]
                for new_elem in children_list[1:]:
                    insert_after.insert_after(new_elem)
                    insert_after = new_elem

            for elem in section['elements_to_remove']:
                if hasattr(elem, 'decompose'):
                    elem.decompose()
        else:  # section
            new_content = BeautifulSoup(updated_html, 'html.parser')

            insert_after = section['insert_after']
            for new_elem in list(new_content.children):
                insert_after.insert_after(new_elem)
                insert_after = new_elem

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
    process_html_start_time = time.perf_counter()

    content = rewrite_urls(content, content_type)

    if not content_type or 'text/html' not in content_type:
        return content

    if not (path.startswith('/wiki/') or path.startswith('wiki/')) or ':' in path:  # Skip special pages like Special:, File:, etc.
        return content

    html_string = content.decode('utf-8')
    processed_html = asyncio.run(process_and_replace_sections_inline(html_string))

    process_html_end_time = time.perf_counter()
    total_time = process_html_end_time - process_html_start_time
    print(f"Total time to process page: {total_time:.6f}")

    return processed_html.encode("utf-8")
