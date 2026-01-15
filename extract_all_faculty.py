"""
Extract All Haverford Faculty
- Get all faculty from https://www.haverford.edu/academics/faculty
- Extract names, departments, and ORCIDs
- Save to JSON file
"""
import json
import re
import logging
from bs4 import BeautifulSoup
from smart_fetcher import SmartFetcher

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def extract_orcid_from_url(url: str) -> str:
    """Extract ORCID ID from URL"""
    # ORCID format: https://orcid.org/0000-0002-1234-5678
    orcid_pattern = r'orcid\.org/(\d{4}-\d{4}-\d{4}-\d{3}[0-9X])'
    match = re.search(orcid_pattern, url)
    if match:
        return match.group(1)
    return None


def extract_orcid_from_text(text: str) -> str:
    """Extract ORCID ID from text"""
    # ORCID format: 0000-0002-1234-5678
    orcid_pattern = r'\b(\d{4}-\d{4}-\d{4}-\d{3}[0-9X])\b'
    match = re.search(orcid_pattern, text)
    if match:
        return match.group(1)
    return None


def normalize_department(dept: str) -> str:
    """Normalize department names"""
    dept_mapping = {
        'computer science': 'Computer Science',
        'cs': 'Computer Science',
        'biology': 'Biology',
        'chemistry': 'Chemistry',
        'physics': 'Physics',
        'mathematics': 'Mathematics',
        'math': 'Mathematics',
        'psychology': 'Psychology',
        'economics': 'Economics',
        'philosophy': 'Philosophy',
        'history': 'History',
        'english': 'English',
        'classics': 'Classics',
        'linguistics': 'Linguistics',
        'political science': 'Political Science',
        'sociology': 'Sociology',
        'anthropology': 'Anthropology',
        'religion': 'Religion',
        'comparative literature': 'Comparative Literature',
        'astronomy': 'Astronomy',
        'geology': 'Geology',
        'environmental studies': 'Environmental Studies',
        'music': 'Music',
        'art': 'Art',
        'visual studies': 'Visual Studies',
        'dance': 'Dance',
        'theater': 'Theater',
    }

    dept_lower = dept.lower().strip()
    return dept_mapping.get(dept_lower, dept.title())


def extract_faculty_from_page(html_content: str) -> list:
    """
    Extract faculty information from the main faculty page
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    faculty_list = []

    logger.info("Parsing faculty page HTML...")

    # Look for faculty listings - try multiple patterns
    # Pattern 1: Individual faculty cards/divs
    faculty_elements = soup.find_all(['div', 'article', 'li'], class_=re.compile(r'faculty|person|profile|staff', re.I))

    if not faculty_elements:
        # Pattern 2: Table rows
        faculty_elements = soup.find_all('tr')

    if not faculty_elements:
        # Pattern 3: Any element with name-like text
        faculty_elements = soup.find_all(['h2', 'h3', 'h4', 'a'], string=re.compile(r'[A-Z][a-z]+ [A-Z][a-z]+'))

    logger.info(f"Found {len(faculty_elements)} potential faculty elements")

    seen_names = set()

    for element in faculty_elements:
        # Extract name
        name = None
        name_element = element.find(['h2', 'h3', 'h4', 'a', 'strong', 'span'], class_=re.compile(r'name|faculty|person', re.I))

        if name_element:
            name = name_element.get_text(strip=True)
        elif element.name in ['h2', 'h3', 'h4', 'a']:
            name = element.get_text(strip=True)

        if not name or len(name) < 3 or len(name) > 100:
            continue

        # Basic name validation
        name_parts = name.split()
        if len(name_parts) < 2 or len(name_parts) > 5:
            continue

        # Skip if not a person name
        non_person_keywords = ['department', 'college', 'university', 'faculty', 'staff', 'directory']
        if any(keyword in name.lower() for keyword in non_person_keywords):
            continue

        # Skip duplicates
        if name in seen_names:
            continue
        seen_names.add(name)

        # Extract department
        department = "Unknown"
        dept_element = element.find(['span', 'div', 'p'], class_=re.compile(r'department|dept|title|position', re.I))
        if dept_element:
            department = normalize_department(dept_element.get_text(strip=True))

        # If no department element, look in surrounding text
        if department == "Unknown":
            surrounding_text = element.get_text()
            # Common department names
            for dept in ['Computer Science', 'Biology', 'Chemistry', 'Physics', 'Mathematics',
                        'Psychology', 'Economics', 'Philosophy', 'History', 'English', 'Classics']:
                if dept.lower() in surrounding_text.lower():
                    department = dept
                    break

        # Extract ORCID
        orcid = None

        # Look for ORCID link
        orcid_link = element.find('a', href=re.compile(r'orcid\.org', re.I))
        if orcid_link:
            orcid = extract_orcid_from_url(orcid_link['href'])

        # Look for ORCID in text
        if not orcid:
            element_text = element.get_text()
            orcid = extract_orcid_from_text(element_text)

        # Extract profile URL
        profile_url = None
        profile_link = element.find('a', href=re.compile(r'/users/|/people/|/faculty/', re.I))
        if profile_link:
            href = profile_link.get('href', '')
            if href.startswith('http'):
                profile_url = href
            elif href.startswith('/'):
                profile_url = f"https://www.haverford.edu{href}"

        faculty_info = {
            'name': name,
            'department': department,
            'orcid': orcid,
            'profile_url': profile_url
        }

        logger.info(f"Found: {name} - {department}" + (f" (ORCID: {orcid})" if orcid else ""))
        faculty_list.append(faculty_info)

    return faculty_list


def fetch_individual_faculty_page(url: str, fetcher: SmartFetcher) -> dict:
    """
    Fetch individual faculty page to get more details including ORCID
    """
    logger.info(f"Fetching individual page: {url}")

    result = fetcher.fetch(url)
    if not result['success']:
        logger.warning(f"Failed to fetch {url}")
        return {}

    content = result['content']

    # Look for ORCID in the content
    orcid = extract_orcid_from_text(content)

    # Look for department if not already set
    department = None
    soup = BeautifulSoup(content, 'html.parser')
    dept_element = soup.find(string=re.compile(r'Department|Division', re.I))
    if dept_element:
        # Get the next text element which might be the department name
        parent = dept_element.parent
        if parent:
            dept_text = parent.get_text()
            for dept in ['Computer Science', 'Biology', 'Chemistry', 'Physics', 'Mathematics']:
                if dept.lower() in dept_text.lower():
                    department = dept
                    break

    return {
        'orcid': orcid,
        'department': department
    }


def main():
    print("="*80)
    print("HAVERFORD FACULTY EXTRACTOR")
    print("="*80)

    faculty_page_url = "https://www.haverford.edu/academics/faculty"

    print(f"\nTarget: {faculty_page_url}")
    print("\nStep 1: Fetching main faculty page...")

    fetcher = SmartFetcher(delay_range=(2.0, 4.0))

    try:
        # Fetch main page
        result = fetcher.fetch(faculty_page_url)

        if not result['success']:
            print(f"ERROR: Could not fetch faculty page")
            print(f"Error: {result.get('error', 'Unknown error')}")
            return

        # Use the content we already fetched - convert it back to HTML-like format
        # The SmartFetcher already got the content, just use that
        print("\nUsing fetched content for parsing...")

        # The result['content'] is extracted text, we need to re-fetch as HTML
        # Let's use requests with the SmartFetcher's session
        import requests

        try:
            # Try simple request first
            fetcher._update_session_headers()
            response = fetcher.session.get(faculty_page_url, timeout=30)
            html_content = response.text
            print(f"Got HTML via direct request ({len(html_content)} characters)")
        except:
            # Fall back to headless browser
            print("Direct request failed, using headless browser...")
            fetcher._init_playwright()
            page = fetcher.playwright_context.new_page()

            try:
                page.goto(faculty_page_url, wait_until='load', timeout=90000)  # Increased timeout, simpler wait condition
                page.wait_for_timeout(5000)  # Wait for dynamic content
                html_content = page.content()
                print(f"Got HTML via headless browser ({len(html_content)} characters)")
            finally:
                page.close()

        # Extract faculty
        print("\nStep 2: Extracting faculty information...")
        faculty_list = extract_faculty_from_page(html_content)

        print(f"\nFound {len(faculty_list)} faculty members")

        # Step 3: Try to get ORCIDs from individual pages for those without
        print("\nStep 3: Fetching individual pages for missing ORCIDs...")

        faculty_without_orcid = [f for f in faculty_list if not f['orcid'] and f['profile_url']]

        if faculty_without_orcid:
            print(f"Checking {len(faculty_without_orcid)} individual pages...")

            for i, faculty in enumerate(faculty_without_orcid[:10], 1):  # Limit to first 10 to save time
                print(f"  [{i}/{min(10, len(faculty_without_orcid))}] {faculty['name']}")

                try:
                    details = fetch_individual_faculty_page(faculty['profile_url'], fetcher)

                    if details.get('orcid'):
                        faculty['orcid'] = details['orcid']
                        print(f"    Found ORCID: {details['orcid']}")

                    if details.get('department') and faculty['department'] == "Unknown":
                        faculty['department'] = details['department']

                except Exception as e:
                    logger.warning(f"Error fetching {faculty['profile_url']}: {e}")

        # Save results
        output_file = "haverford_all_faculty.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(faculty_list, f, indent=2, ensure_ascii=False)

        print(f"\n{'='*80}")
        print("RESULTS")
        print('='*80)
        print(f"Total faculty extracted: {len(faculty_list)}")
        print(f"Saved to: {output_file}")

        # Statistics
        with_orcid = len([f for f in faculty_list if f['orcid']])
        with_dept = len([f for f in faculty_list if f['department'] != 'Unknown'])

        print(f"\nStatistics:")
        print(f"  With ORCID: {with_orcid}/{len(faculty_list)} ({with_orcid*100//len(faculty_list) if faculty_list else 0}%)")
        print(f"  With Department: {with_dept}/{len(faculty_list)} ({with_dept*100//len(faculty_list) if faculty_list else 0}%)")

        # Show sample
        print(f"\nSample (first 10):")
        for i, faculty in enumerate(faculty_list[:10], 1):
            orcid_str = f"ORCID: {faculty['orcid']}" if faculty['orcid'] else "No ORCID"
            print(f"{i:2d}. {faculty['name']:30s} | {faculty['department']:25s} | {orcid_str}")

        if len(faculty_list) > 10:
            print(f"\n... and {len(faculty_list) - 10} more")

        # By department
        print(f"\nBy Department:")
        from collections import Counter
        dept_counts = Counter(f['department'] for f in faculty_list)
        for dept, count in dept_counts.most_common():
            print(f"  {dept}: {count}")

    finally:
        fetcher.close()

    print("\n" + "="*80)
    print("COMPLETE!")
    print("="*80)
    print(f"\nAll faculty data saved to: {output_file}")
    print("\nNext steps:")
    print("  1. Review the JSON file")
    print("  2. Update any missing ORCIDs manually if needed")
    print("  3. Use this data to populate your database")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
