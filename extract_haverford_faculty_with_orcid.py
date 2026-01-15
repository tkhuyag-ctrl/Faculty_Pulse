"""
Extract all Haverford faculty with their departments and ORCID identifiers
Uses the existing crawler infrastructure
"""
import json
import re
import logging
from typing import List, Dict, Optional
from smart_fetcher import SmartFetcher
from bs4 import BeautifulSoup
from urllib.parse import urljoin

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('haverford_faculty_orcid.log')
    ]
)

logger = logging.getLogger(__name__)


def extract_orcid_from_text(text: str) -> Optional[str]:
    """Extract ORCID ID from text using regex"""
    # ORCID format: 0000-0000-0000-0000 (16 digits with hyphens)
    orcid_pattern = r'\b\d{4}-\d{4}-\d{4}-\d{3}[0-9X]\b'
    match = re.search(orcid_pattern, text)
    if match:
        return match.group(0)
    return None


def extract_orcid_from_url(url: str) -> Optional[str]:
    """Extract ORCID ID from ORCID URL"""
    # Match orcid.org URLs
    orcid_url_pattern = r'orcid\.org/(\d{4}-\d{4}-\d{4}-\d{3}[0-9X])'
    match = re.search(orcid_url_pattern, url)
    if match:
        return match.group(1)
    return None


def search_orcid_in_page(html_content: str, base_url: str) -> Optional[str]:
    """Search for ORCID in page content and links"""
    soup = BeautifulSoup(html_content, 'html.parser')

    # Strategy 1: Look for ORCID links
    for link in soup.find_all('a', href=True):
        href = link['href']
        if 'orcid.org' in href.lower():
            orcid = extract_orcid_from_url(href)
            if orcid:
                logger.info(f"Found ORCID in link: {orcid}")
                return orcid

    # Strategy 2: Look for ORCID icon/image
    for img in soup.find_all('img'):
        src = img.get('src', '')
        alt = img.get('alt', '')
        if 'orcid' in src.lower() or 'orcid' in alt.lower():
            # Check nearby text or parent link
            parent = img.find_parent('a')
            if parent and parent.get('href'):
                orcid = extract_orcid_from_url(parent['href'])
                if orcid:
                    logger.info(f"Found ORCID from image link: {orcid}")
                    return orcid

    # Strategy 3: Search for ORCID in text content
    text_content = soup.get_text()
    orcid = extract_orcid_from_text(text_content)
    if orcid:
        logger.info(f"Found ORCID in text: {orcid}")
        return orcid

    # Strategy 4: Look for meta tags
    for meta in soup.find_all('meta'):
        content = meta.get('content', '')
        if 'orcid' in content.lower():
            orcid = extract_orcid_from_text(content)
            if orcid:
                logger.info(f"Found ORCID in meta tag: {orcid}")
                return orcid

    return None


def extract_faculty_from_main_page(fetcher: SmartFetcher, url: str) -> List[Dict]:
    """Extract faculty list from main faculty page"""
    logger.info(f"Fetching main faculty page: {url}")

    # Try multiple strategies to avoid 403
    html_content = None

    # Strategy 1: Try with playwright directly first (most reliable for 403)
    try:
        logger.info("Trying playwright...")
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            page = context.new_page()
            page.goto(url, wait_until='networkidle', timeout=60000)
            page.wait_for_timeout(3000)
            html_content = page.content()
            page.close()
            context.close()
            browser.close()
            logger.info("Playwright succeeded")
    except Exception as e:
        logger.warning(f"Playwright failed: {e}")

    # Strategy 2: Direct request with enhanced headers (fallback)
    if html_content is None:
        try:
            # Add more realistic headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
                'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"'
            }

            import requests
            session = requests.Session()
            session.headers.update(headers)

            fetcher._random_delay()
            response = session.get(url, timeout=30, allow_redirects=True)
            response.raise_for_status()
            html_content = response.text
            logger.info("Direct request with enhanced headers succeeded")
        except Exception as e:
            logger.error(f"Enhanced direct request failed: {e}")

    if html_content is None:
        logger.error("All strategies failed")
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
    faculty_list = []

    logger.info("Parsing faculty information...")

    # Look for faculty listings - Haverford typically uses specific patterns
    # Try multiple selectors to catch different page structures

    # Strategy 1: Look for links with faculty in URL
    for link in soup.find_all('a', href=True):
        href = link['href']
        # Faculty pages typically have /faculty/ or /users/ in URL
        if '/faculty/' in href or '/users/' in href or '/people/' in href:
            faculty_url = urljoin(url, href)
            faculty_name = link.get_text(strip=True)

            # Skip if name is too short or looks like navigation
            if len(faculty_name) < 3 or len(faculty_name) > 100:
                continue

            # Skip common navigation terms
            skip_terms = ['faculty', 'staff', 'directory', 'all', 'view', 'more',
                         'contact', 'home', 'back', 'search', 'filter']
            if any(term in faculty_name.lower() for term in skip_terms):
                continue

            # Try to find department nearby
            department = "Unknown"

            # Look at parent elements for department info
            parent = link.find_parent(['div', 'li', 'tr', 'article'])
            if parent:
                # Look for department class or text
                dept_elem = parent.find(class_=re.compile(r'department|dept|division', re.I))
                if dept_elem:
                    department = dept_elem.get_text(strip=True)
                else:
                    # Look for any text that looks like a department
                    parent_text = parent.get_text()
                    dept_keywords = ['biology', 'chemistry', 'physics', 'mathematics', 'computer science',
                                   'psychology', 'economics', 'history', 'english', 'philosophy',
                                   'political science', 'sociology', 'anthropology', 'classics',
                                   'art', 'music', 'religion', 'astronomy', 'environmental']
                    for keyword in dept_keywords:
                        if keyword in parent_text.lower():
                            department = keyword.title()
                            break

            faculty_list.append({
                'name': faculty_name,
                'department': department,
                'profile_url': faculty_url,
                'orcid': None  # Will be filled later
            })

    # Strategy 2: Look for structured faculty cards/listings
    # Common patterns: .faculty-card, .person, .profile-card, etc.
    for card in soup.find_all(['div', 'li', 'article'], class_=re.compile(r'faculty|person|profile|staff', re.I)):
        # Extract name
        name_elem = card.find(['h1', 'h2', 'h3', 'h4', 'a', 'span'], class_=re.compile(r'name|title', re.I))
        if not name_elem:
            name_elem = card.find(['h1', 'h2', 'h3', 'h4'])

        if name_elem:
            faculty_name = name_elem.get_text(strip=True)

            # Find profile link
            profile_link = card.find('a', href=True)
            faculty_url = urljoin(url, profile_link['href']) if profile_link else None

            # Find department
            dept_elem = card.find(class_=re.compile(r'department|dept|division', re.I))
            department = dept_elem.get_text(strip=True) if dept_elem else "Unknown"

            if faculty_name and len(faculty_name) > 3:
                # Check if already added
                if not any(f['name'] == faculty_name for f in faculty_list):
                    faculty_list.append({
                        'name': faculty_name,
                        'department': department,
                        'profile_url': faculty_url,
                        'orcid': None
                    })

    logger.info(f"Found {len(faculty_list)} faculty members on main page")
    return faculty_list


def find_faculty_orcid(fetcher: SmartFetcher, faculty: Dict) -> Optional[str]:
    """Try to find ORCID for a faculty member"""
    logger.info(f"Searching for ORCID: {faculty['name']}")

    # If we have a profile URL, check there first
    if faculty['profile_url']:
        try:
            fetcher._random_delay()
            fetcher._update_session_headers()

            logger.info(f"  Checking profile: {faculty['profile_url']}")
            response = fetcher.session.get(faculty['profile_url'], timeout=30)
            response.raise_for_status()
            html_content = response.text

            orcid = search_orcid_in_page(html_content, faculty['profile_url'])
            if orcid:
                logger.info(f"  ✓ Found ORCID: {orcid}")
                return orcid

        except Exception as e:
            logger.warning(f"  Failed to fetch profile page: {e}")

            # Try with headless browser
            try:
                fetcher._init_playwright()
                page = fetcher.playwright_context.new_page()
                page.goto(faculty['profile_url'], wait_until='networkidle', timeout=30000)
                page.wait_for_timeout(2000)
                html_content = page.content()
                page.close()

                orcid = search_orcid_in_page(html_content, faculty['profile_url'])
                if orcid:
                    logger.info(f"  ✓ Found ORCID (headless): {orcid}")
                    return orcid

            except Exception as e2:
                logger.warning(f"  Headless browser also failed: {e2}")

    logger.info(f"  ✗ No ORCID found for {faculty['name']}")
    return None


def main():
    """Main execution function"""
    print("="*80)
    print("HAVERFORD FACULTY + ORCID EXTRACTOR")
    print("="*80)

    faculty_page_url = "https://www.haverford.edu/academics/faculty"

    print(f"\nTarget: {faculty_page_url}")
    print("Tasks:")
    print("  1. Extract all faculty names and departments")
    print("  2. Find ORCID identifiers for each faculty")
    print()

    # Initialize fetcher
    fetcher = SmartFetcher(
        use_proxies=False,
        delay_range=(2.0, 4.0),  # Slower to avoid 403s
        max_retries=3
    )

    try:
        # Step 1: Extract faculty from main page
        print("Step 1: Extracting faculty from main page...")
        faculty_list = extract_faculty_from_main_page(fetcher, faculty_page_url)

        if not faculty_list:
            print("\nNo faculty found. The page structure might have changed.")
            print("  Check the log file for details: haverford_faculty_orcid.log")
            return

        print(f"\nFound {len(faculty_list)} faculty members")

        # Show preview
        print("\nPreview of first 5 faculty:")
        for i, faculty in enumerate(faculty_list[:5], 1):
            print(f"  {i}. {faculty['name']} - {faculty['department']}")

        # Step 2: Find ORCIDs
        print("\n" + "="*80)
        print("Step 2: Finding ORCID identifiers...")
        print("="*80)
        print("This may take several minutes...\n")

        faculty_with_orcid = 0

        for i, faculty in enumerate(faculty_list, 1):
            print(f"[{i}/{len(faculty_list)}] Processing: {faculty['name']}")

            orcid = find_faculty_orcid(fetcher, faculty)
            if orcid:
                faculty['orcid'] = orcid
                faculty_with_orcid += 1
                print(f"  ORCID: {orcid}")
            else:
                print(f"  No ORCID found")

        # Step 3: Save results
        print("\n" + "="*80)
        print("Step 3: Saving results...")
        print("="*80)

        output_file = "haverford_faculty_with_orcid.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(faculty_list, f, indent=2, ensure_ascii=False)

        print(f"\nSaved to: {output_file}")

        # Summary
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        print(f"Total faculty: {len(faculty_list)}")
        print(f"With ORCID: {faculty_with_orcid}")
        print(f"Without ORCID: {len(faculty_list) - faculty_with_orcid}")
        print(f"ORCID coverage: {faculty_with_orcid/len(faculty_list)*100:.1f}%")

        # Show faculty with ORCIDs
        if faculty_with_orcid > 0:
            print(f"\nFaculty with ORCID identifiers:")
            for faculty in faculty_list:
                if faculty['orcid']:
                    print(f"  - {faculty['name']} ({faculty['department']}): {faculty['orcid']}")

        print("\n" + "="*80)

    finally:
        fetcher.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
