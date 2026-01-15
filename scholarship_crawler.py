"""
Haverford Scholarship Repository Crawler
Crawl https://scholarship.haverford.edu/ for faculty publications and documents
Match with CS faculty who have OpenAlex IDs
Store in ChromaDB
"""
import json
import logging
import re
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup
from chroma_manager import ChromaDBManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scholarship_crawler.log')
    ]
)

logger = logging.getLogger(__name__)


class ScholarshipCrawler:
    """Crawl Haverford scholarship repository for faculty publications"""

    def __init__(self):
        self.chroma = ChromaDBManager()
        self.base_url = "https://scholarship.haverford.edu"
        self.results = []

        # Initialize Playwright
        self.playwright = None
        self.browser = None
        self.context = None

    def init_browser(self):
        """Initialize Playwright browser"""
        if self.playwright is None:
            logger.info("Initializing Playwright browser...")
            self.playwright = sync_playwright().start()

            self.browser = self.playwright.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )

            self.context = self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )

            self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)

            logger.info("Browser initialized")

    def fetch_page(self, url: str, wait_time: int = 3000) -> Optional[str]:
        """Fetch page content"""
        try:
            if self.context is None:
                self.init_browser()

            page = self.context.new_page()

            try:
                logger.info(f"Fetching: {url}")
                page.goto(url, wait_until='domcontentloaded', timeout=20000)
                page.wait_for_timeout(wait_time)
                content = page.content()
                logger.info(f"Fetched {len(content)} characters")
                return content

            except PlaywrightTimeout:
                logger.warning(f"Timeout fetching {url}")
                return None
            finally:
                page.close()

        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def search_faculty_on_scholarship(self, faculty_name: str) -> List[Dict]:
        """Search for a faculty member on scholarship.haverford.edu"""
        logger.info(f"Searching scholarship repository for: {faculty_name}")

        # Build search URL
        search_query = faculty_name.replace(' ', '+')
        search_url = f"{self.base_url}/do/search/?q={search_query}&start=0&context=509156"

        html = self.fetch_page(search_url, wait_time=5000)

        if not html:
            logger.warning(f"Could not fetch search results for {faculty_name}")
            return []

        soup = BeautifulSoup(html, 'html.parser')
        publications = []

        # Look for publication entries in search results
        # The structure may vary, so we'll look for common patterns
        for article in soup.find_all(['article', 'div'], class_=re.compile('result|publication|item', re.I)):
            pub_data = {}

            # Try to extract title
            title_elem = article.find(['h2', 'h3', 'h4', 'a'], class_=re.compile('title', re.I))
            if not title_elem:
                title_elem = article.find('a')

            if title_elem:
                pub_data['title'] = title_elem.get_text(strip=True)
                pub_data['url'] = title_elem.get('href', '')
                if pub_data['url'] and not pub_data['url'].startswith('http'):
                    pub_data['url'] = f"{self.base_url}{pub_data['url']}"

            # Try to extract date/year
            date_elem = article.find(text=re.compile(r'\b(19|20)\d{2}\b'))
            if date_elem:
                year_match = re.search(r'\b(19|20)\d{2}\b', str(date_elem))
                if year_match:
                    pub_data['year'] = int(year_match.group())

            # Extract description/abstract if available
            desc_elem = article.find(['p', 'div'], class_=re.compile('abstract|description|summary', re.I))
            if desc_elem:
                pub_data['description'] = desc_elem.get_text(strip=True)[:500]

            if pub_data.get('title'):
                publications.append(pub_data)

        logger.info(f"Found {len(publications)} publications for {faculty_name}")
        return publications

    def fetch_publication_details(self, pub_url: str) -> Optional[Dict]:
        """Fetch full details of a publication"""
        logger.info(f"Fetching publication details: {pub_url}")

        html = self.fetch_page(pub_url, wait_time=3000)

        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')

        details = {}

        # Try to extract full abstract/content
        abstract = soup.find(['div', 'section'], class_=re.compile('abstract|description', re.I))
        if abstract:
            details['abstract'] = abstract.get_text(separator='\n', strip=True)

        # Look for PDF link
        pdf_link = soup.find('a', href=re.compile(r'\.pdf$', re.I))
        if pdf_link:
            details['pdf_url'] = pdf_link.get('href', '')
            if details['pdf_url'] and not details['pdf_url'].startswith('http'):
                details['pdf_url'] = f"{self.base_url}{details['pdf_url']}"

        # Look for metadata
        for meta in soup.find_all('meta'):
            name = meta.get('name', '').lower()
            if 'author' in name:
                details['authors'] = meta.get('content', '')
            elif 'date' in name or 'published' in name:
                details['date'] = meta.get('content', '')

        return details

    def store_publication(self, pub: Dict, faculty_info: Dict) -> bool:
        """Store publication in ChromaDB"""
        try:
            # Build content
            content_parts = [
                f"Title: {pub.get('title', 'Untitled')}",
            ]

            if pub.get('authors'):
                content_parts.append(f"Authors: {pub['authors']}")
            else:
                content_parts.append(f"Author: {faculty_info['name']}")

            if pub.get('year'):
                content_parts.append(f"Year: {pub['year']}")

            if pub.get('date'):
                content_parts.append(f"Date: {pub['date']}")

            if pub.get('description'):
                content_parts.append(f"\n{pub['description']}")

            if pub.get('abstract'):
                content_parts.append(f"\nAbstract: {pub['abstract']}")

            if pub.get('url'):
                content_parts.append(f"\nURL: {pub['url']}")

            if pub.get('pdf_url'):
                content_parts.append(f"PDF: {pub['pdf_url']}")

            content = '\n'.join(content_parts)

            # Store in ChromaDB
            self.chroma.add_single_submission(
                document=content,
                faculty_name=faculty_info['name'],
                date_published=pub.get('date', pub.get('year', '')),
                content_type='Publication',
                department=faculty_info.get('department', 'Computer Science'),
                submission_id=None
            )

            logger.info(f"Stored publication: {pub.get('title', 'Untitled')[:50]}")
            return True

        except Exception as e:
            logger.error(f"Error storing publication: {e}")
            return False

    def process_faculty(self, faculty_info: Dict) -> Dict:
        """Process one faculty member"""
        name = faculty_info['name']

        logger.info(f"\n{'='*60}")
        logger.info(f"Processing: {name}")
        logger.info(f"OpenAlex ID: {faculty_info.get('openalex_id', 'N/A')}")

        result = {
            'name': name,
            'openalex_id': faculty_info.get('openalex_id'),
            'publications_found': 0,
            'publications_stored': 0,
            'error': None
        }

        try:
            # Search scholarship repository
            publications = self.search_faculty_on_scholarship(name)
            result['publications_found'] = len(publications)

            if not publications:
                logger.info(f"No publications found for {name}")
                return result

            # Filter for 2020+ publications
            recent_pubs = [
                p for p in publications
                if p.get('year') and p['year'] >= 2020
            ]

            logger.info(f"Found {len(recent_pubs)} publications from 2020+")

            # Fetch details and store
            for pub in recent_pubs:
                if pub.get('url'):
                    details = self.fetch_publication_details(pub['url'])
                    if details:
                        pub.update(details)

                if self.store_publication(pub, faculty_info):
                    result['publications_stored'] += 1

        except Exception as e:
            logger.error(f"Error processing {name}: {e}")
            result['error'] = str(e)

        return result

    def load_cs_faculty(self, json_file: str) -> List[Dict]:
        """Load CS faculty with OpenAlex IDs"""
        logger.info(f"Loading faculty from: {json_file}")

        with open(json_file, 'r', encoding='utf-8') as f:
            all_faculty = json.load(f)

        cs_faculty = [
            f for f in all_faculty
            if f.get('department') == 'Computer Science' and
               f.get('openalex_id') and
               f['openalex_id'] != 'null'
        ]

        logger.info(f"Found {len(cs_faculty)} CS faculty with OpenAlex IDs")
        return cs_faculty

    def cleanup(self):
        """Clean up browser resources"""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def run(self, json_file: str = "haverford_faculty_with_openalex.json"):
        """Main execution"""
        print("="*80)
        print("HAVERFORD SCHOLARSHIP REPOSITORY CRAWLER")
        print("="*80)
        print(f"\nSearching: {self.base_url}")
        print("Target: CS faculty with OpenAlex IDs")
        print("Date filter: 2020+")
        print()

        try:
            # Load faculty
            faculty_list = self.load_cs_faculty(json_file)

            if not faculty_list:
                print("No CS faculty with OpenAlex IDs found!")
                return

            print(f"Found {len(faculty_list)} CS faculty")
            print()

            # Process each
            for i, faculty in enumerate(faculty_list, 1):
                print(f"\n[{i}/{len(faculty_list)}] {faculty['name']}")

                result = self.process_faculty(faculty)
                self.results.append(result)

                if result['publications_stored'] > 0:
                    print(f"  SUCCESS: {result['publications_stored']} publications stored")
                elif result['publications_found'] > 0:
                    print(f"  PARTIAL: {result['publications_found']} found, {result['publications_stored']} stored")
                else:
                    print(f"  NO PUBLICATIONS FOUND")

            # Summary
            print("\n" + "="*80)
            print("SUMMARY")
            print("="*80)
            total_found = sum(r['publications_found'] for r in self.results)
            total_stored = sum(r['publications_stored'] for r in self.results)

            print(f"Faculty processed: {len(self.results)}")
            print(f"Publications found: {total_found}")
            print(f"Publications stored: {total_stored}")

            # Save results
            results_file = "scholarship_crawler_results.json"
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2)

            print(f"\nResults saved to: {results_file}")
            print()

        finally:
            self.cleanup()


if __name__ == "__main__":
    crawler = ScholarshipCrawler()
    crawler.run()
