"""
Crawl Haverford faculty page to get official department assignments
"""
import sys
import requests
from bs4 import BeautifulSoup
import json
import time

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

def crawl_faculty_page():
    """Crawl the Haverford faculty directory"""
    url = "https://www.haverford.edu/academics/faculty"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    print(f"\nFetching: {url}\n")

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Save HTML for inspection
        with open('haverford_faculty_page.html', 'w', encoding='utf-8') as f:
            f.write(soup.prettify())
        print("✓ Saved HTML to haverford_faculty_page.html")

        # Try to find faculty listings
        faculty_data = []

        # Look for common patterns in faculty listings
        # Pattern 1: Look for faculty cards/divs
        faculty_cards = soup.find_all(['div', 'article', 'li'], class_=lambda x: x and ('faculty' in x.lower() or 'person' in x.lower()))

        print(f"\nFound {len(faculty_cards)} potential faculty elements")

        # Pattern 2: Look for links to faculty pages
        faculty_links = soup.find_all('a', href=lambda x: x and '/user/' in x)

        print(f"Found {len(faculty_links)} faculty profile links")

        # Pattern 3: Extract text and look for department headings
        text_content = soup.get_text()

        # Try to parse the page structure
        print("\n" + "="*80)
        print("PAGE STRUCTURE ANALYSIS")
        print("="*80)

        # Find all headings that might be departments
        headings = soup.find_all(['h2', 'h3', 'h4'])
        print(f"\nFound {len(headings)} headings")

        for heading in headings[:10]:  # Show first 10
            print(f"  - {heading.get_text(strip=True)}")

        # Look for specific class patterns
        all_classes = set()
        for tag in soup.find_all(True):
            if tag.get('class'):
                for cls in tag.get('class'):
                    all_classes.add(cls)

        print(f"\nTotal unique CSS classes: {len(all_classes)}")
        faculty_classes = [c for c in all_classes if 'faculty' in c.lower() or 'person' in c.lower() or 'staff' in c.lower()]
        print(f"Faculty-related classes: {len(faculty_classes)}")
        for cls in faculty_classes[:20]:
            print(f"  - {cls}")

        return faculty_data

    except requests.exceptions.RequestException as e:
        print(f"✗ Error fetching page: {e}")
        return None


def main():
    print("\n" + "="*80)
    print("HAVERFORD FACULTY PAGE CRAWLER")
    print("="*80)

    faculty_data = crawl_faculty_page()

    if faculty_data is not None:
        print("\n" + "="*80)
        print("NEXT STEPS")
        print("="*80)
        print("""
1. Review haverford_faculty_page.html to understand the page structure
2. Identify the correct HTML elements containing faculty names and departments
3. Update this script with the correct selectors
4. Re-run to extract all faculty department assignments
        """)


if __name__ == "__main__":
    main()
