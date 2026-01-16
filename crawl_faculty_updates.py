"""
Crawl Haverford faculty update pages to extract awards, grants, and talks
Using enhanced crawler infrastructure
"""
import sys
import requests
from bs4 import BeautifulSoup
import json
import time
import re
from datetime import datetime

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# All faculty update URLs from 2021-2025
FACULTY_UPDATE_URLS = [
    # 2025
    "https://www.haverford.edu/college-communications/news/winter-2025-faculty-update",
    "https://www.haverford.edu/marketing-and-communications/news/spring-2025-faculty-update",
    "https://www.haverford.edu/marketing-and-communications/news/fall-2025-faculty-update",
    # 2024
    "https://www.haverford.edu/college-communications/news/summer-2024-faculty-update",
    "https://www.haverford.edu/college-communications/news/fall-2024-faculty-update",
    "https://www.haverford.edu/college-communications/news/spring-2024-faculty-update",
    "https://www.haverford.edu/college-communications/news/winter-2024-faculty-update",
    # 2023
    "https://www.haverford.edu/college-communications/news/summer-2023-faculty-update",
    "https://www.haverford.edu/college-communications/news/spring-2023-faculty-update",
    # 2022
    "https://www.haverford.edu/college-communications/news/spring-faculty-updates-2022",
    "https://www.haverford.edu/college-communications/news/winter-2022-faculty-update",
    # 2021 - try common patterns
    "https://www.haverford.edu/college-communications/news/fall-2021-faculty-update",
    "https://www.haverford.edu/college-communications/news/summer-2021-faculty-update",
    "https://www.haverford.edu/college-communications/news/spring-2021-faculty-update",
]


def try_multiple_methods(url):
    """Try multiple HTTP methods to access the URL"""

    methods = [
        {
            "name": "Method 1: Standard browser",
            "headers": {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        },
        {
            "name": "Method 2: Firefox",
            "headers": {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
            }
        },
        {
            "name": "Method 3: Simple",
            "headers": {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        },
    ]

    for method in methods:
        try:
            session = requests.Session()
            response = session.get(url, headers=method['headers'], timeout=30, allow_redirects=True)

            if response.status_code == 200:
                return response, method['name']

        except Exception as e:
            continue

    return None, None


def extract_faculty_achievements(html_content, url):
    """Extract faculty names and their achievements from HTML"""
    soup = BeautifulSoup(html_content, 'html.parser')

    # Extract the main content
    # Try different content selectors
    content_div = (
        soup.find('div', class_='field-item') or
        soup.find('div', class_='content') or
        soup.find('article') or
        soup.find('main')
    )

    if not content_div:
        return []

    achievements = []

    # Get all paragraphs
    paragraphs = content_div.find_all('p')

    for p in paragraphs:
        text = p.get_text(strip=True)

        if not text or len(text) < 20:
            continue

        # Try to identify faculty names (usually at the start, often with titles)
        # Pattern: Name (Department/Title) did something
        # or: Name, Department, did something

        # Look for achievement keywords
        achievement_keywords = [
            'award', 'grant', 'fellowship', 'prize', 'honor',
            'presented', 'talk', 'keynote', 'lecture', 'conference',
            'published', 'book', 'article', 'paper',
            'received', 'won', 'selected', 'named', 'appointed'
        ]

        text_lower = text.lower()
        has_achievement = any(keyword in text_lower for keyword in achievement_keywords)

        if has_achievement:
            achievements.append({
                'text': text,
                'source_url': url,
                'raw_html': str(p)
            })

    return achievements


def parse_achievement_type(text):
    """Determine if achievement is Award, Talk, or Publication"""
    text_lower = text.lower()

    # Award keywords
    if any(word in text_lower for word in ['award', 'grant', 'fellowship', 'prize', 'honor', 'received', 'won', 'named to']):
        return 'Award'

    # Talk keywords
    if any(word in text_lower for word in ['presented', 'talk', 'keynote', 'lecture', 'conference', 'symposium', 'panel']):
        return 'Talk'

    # Publication keywords
    if any(word in text_lower for word in ['published', 'book', 'article', 'paper', 'journal', 'chapter']):
        return 'Publication'

    return 'Unknown'


def extract_year_from_url(url):
    """Extract year from URL"""
    match = re.search(r'(202[0-9])', url)
    if match:
        return match.group(1)
    return None


def main():
    print("\n" + "="*80)
    print("CRAWLING HAVERFORD FACULTY UPDATES (2021-2025)")
    print("="*80 + "\n")

    all_achievements = []
    successful_urls = []
    failed_urls = []

    for i, url in enumerate(FACULTY_UPDATE_URLS, 1):
        print(f"\n[{i}/{len(FACULTY_UPDATE_URLS)}] Attempting: {url}")

        response, method = try_multiple_methods(url)

        if response:
            print(f"  ✓ SUCCESS with {method}")
            successful_urls.append(url)

            # Extract achievements
            achievements = extract_faculty_achievements(response.content, url)
            print(f"  → Found {len(achievements)} potential achievements")

            # Add year from URL
            year = extract_year_from_url(url)
            for achievement in achievements:
                achievement['year'] = year
                achievement['content_type'] = parse_achievement_type(achievement['text'])

            all_achievements.extend(achievements)

            # Save HTML for manual inspection
            filename = url.split('/')[-1] + '.html'
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f"  → Saved HTML to {filename}")

        else:
            print(f"  ✗ FAILED - All methods blocked")
            failed_urls.append(url)

        # Be polite - wait between requests
        time.sleep(1)

    # Summary
    print("\n\n" + "="*80)
    print("CRAWLING SUMMARY")
    print("="*80)
    print(f"\nSuccessful: {len(successful_urls)}/{len(FACULTY_UPDATE_URLS)}")
    print(f"Failed: {len(failed_urls)}/{len(FACULTY_UPDATE_URLS)}")
    print(f"Total achievements found: {len(all_achievements)}")

    # Breakdown by type
    type_counts = {}
    for achievement in all_achievements:
        content_type = achievement['content_type']
        type_counts[content_type] = type_counts.get(content_type, 0) + 1

    print("\nBy content type:")
    for content_type, count in sorted(type_counts.items()):
        print(f"  {content_type}: {count}")

    # Save all achievements to JSON
    output_file = 'faculty_achievements_raw.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_achievements, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Saved all achievements to {output_file}")

    # Show sample achievements
    print("\n" + "="*80)
    print("SAMPLE ACHIEVEMENTS")
    print("="*80)

    for achievement in all_achievements[:10]:
        print(f"\n[{achievement['content_type']}] ({achievement['year']})")
        print(f"  {achievement['text'][:200]}...")

    if failed_urls:
        print("\n" + "="*80)
        print("FAILED URLS")
        print("="*80)
        for url in failed_urls:
            print(f"  {url}")

    return all_achievements


if __name__ == "__main__":
    main()
