"""
Extract all Haverford faculty with their departments - Fast version
Skips slow individual page crawling, focuses on main directory
"""
import json
import re
import logging
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('haverford_faculty_fast.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


def extract_faculty_with_playwright(url: str) -> List[Dict]:
    """Extract faculty list using Playwright"""
    logger.info(f"Fetching faculty page: {url}")

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            page = context.new_page()
            logger.info("Navigating to page...")
            page.goto(url, wait_until='networkidle', timeout=60000)
            page.wait_for_timeout(3000)
            html_content = page.content()
            page.close()
            context.close()
            browser.close()
            logger.info("Successfully fetched page")
    except Exception as e:
        logger.error(f"Failed to fetch page: {e}")
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
    faculty_list = []

    logger.info("Parsing faculty information...")

    # Find all faculty links - Haverford uses /users/ pattern
    faculty_links = soup.find_all('a', href=re.compile(r'/users/\w+'))

    seen_names = set()

    for link in faculty_links:
        faculty_name = link.get_text(strip=True)
        href = link['href']

        # Skip if name is too short or already seen
        if len(faculty_name) < 3 or faculty_name in seen_names:
            continue

        # Skip navigation terms
        skip_terms = ['faculty', 'staff', 'directory', 'all', 'view', 'more',
                     'contact', 'home', 'back', 'search', 'filter', 'login']
        if any(term in faculty_name.lower() for term in skip_terms):
            continue

        seen_names.add(faculty_name)

        # Get full profile URL
        profile_url = urljoin(url, href)

        # Try to extract department from nearby content
        department = "Unknown"

        # Look at parent elements
        parent = link.find_parent(['div', 'li', 'tr', 'article', 'td'])
        if parent:
            # Try to find department in parent
            parent_text = parent.get_text()

            # Common department patterns
            dept_patterns = {
                r'\b(computer science|cs)\b': 'Computer Science',
                r'\b(biology|bio)\b': 'Biology',
                r'\b(chemistry|chem)\b': 'Chemistry',
                r'\b(physics)\b': 'Physics',
                r'\b(mathematics|math)\b': 'Mathematics',
                r'\b(psychology|psych)\b': 'Psychology',
                r'\b(economics|econ)\b': 'Economics',
                r'\b(history)\b': 'History',
                r'\b(english)\b': 'English',
                r'\b(philosophy|phil)\b': 'Philosophy',
                r'\b(political science|poli sci)\b': 'Political Science',
                r'\b(sociology|soc)\b': 'Sociology',
                r'\b(anthropology|anthro)\b': 'Anthropology',
                r'\b(classics)\b': 'Classics',
                r'\b(fine arts|art)\b': 'Fine Arts',
                r'\b(music)\b': 'Music',
                r'\b(religion)\b': 'Religion',
                r'\b(astronomy|astro)\b': 'Astronomy',
                r'\b(environmental)\b': 'Environmental Studies'
            }

            for pattern, dept_name in dept_patterns.items():
                if re.search(pattern, parent_text, re.IGNORECASE):
                    department = dept_name
                    break

        faculty_list.append({
            'name': faculty_name,
            'department': department,
            'profile_url': profile_url,
            'orcid': None  # To be filled later
        })

        logger.info(f"  Found: {faculty_name} - {department}")

    logger.info(f"Total faculty found: {len(faculty_list)}")
    return faculty_list


def main():
    """Main execution function"""
    print("="*80)
    print("HAVERFORD FACULTY EXTRACTOR (FAST)")
    print("="*80)

    faculty_page_url = "https://www.haverford.edu/academics/faculty"

    print(f"\nTarget: {faculty_page_url}")
    print("Extracting faculty names, departments, and profile URLs...")
    print()

    # Extract faculty
    faculty_list = extract_faculty_with_playwright(faculty_page_url)

    if not faculty_list:
        print("\nNo faculty found. Check the log file: haverford_faculty_fast.log")
        return

    print(f"\nFound {len(faculty_list)} faculty members")

    # Save results
    output_file = "haverford_faculty_with_orcid.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(faculty_list, f, indent=2, ensure_ascii=False)

    print(f"Saved to: {output_file}")

    # Summary by department
    dept_counts = {}
    for faculty in faculty_list:
        dept = faculty['department']
        dept_counts[dept] = dept_counts.get(dept, 0) + 1

    print("\n" + "="*80)
    print("SUMMARY BY DEPARTMENT")
    print("="*80)
    for dept, count in sorted(dept_counts.items(), key=lambda x: -x[1]):
        print(f"  {dept}: {count} faculty")

    print("\n" + "="*80)
    print("FACULTY LIST")
    print("="*80)
    for i, faculty in enumerate(faculty_list, 1):
        print(f"{i:3d}. {faculty['name']:<40} {faculty['department']}")

    print("\n" + "="*80)
    print(f"Total: {len(faculty_list)} faculty members")
    print(f"Saved to: {output_file}")
    print("="*80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
