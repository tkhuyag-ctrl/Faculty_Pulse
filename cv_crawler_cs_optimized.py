"""
Optimized CV Crawler for CS Faculty
- Focus on Computer Science faculty from https://www.haverford.edu/computer-science/faculty-staff
- Use headless browser from the start (skip slow direct requests)
- Enhanced anti-bot detection
- Extract CVs and store in ChromaDB
"""
import os
import re
import json
import logging
from datetime import datetime
from typing import Optional, Dict, List
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from chroma_manager import ChromaDBManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('cv_crawler_cs_optimized.log')
    ]
)

logger = logging.getLogger(__name__)


class OptimizedCVCrawler:
    """Optimized CV crawler using headless browser with anti-bot measures"""

    def __init__(self, cv_dir: str = "./faculty_cvs"):
        self.chroma = ChromaDBManager()
        self.cv_dir = Path(cv_dir)
        self.cv_dir.mkdir(exist_ok=True)
        self.results = []

        # Initialize Playwright once and reuse
        self.playwright = None
        self.browser = None
        self.context = None

    def init_browser(self):
        """Initialize Playwright browser with anti-bot settings"""
        if self.playwright is None:
            logger.info("Initializing Playwright browser...")
            self.playwright = sync_playwright().start()

            # Launch with stealth settings
            self.browser = self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                ]
            )

            # Create context with realistic settings
            self.context = self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                ignore_https_errors=True
            )

            # Anti-detection: remove webdriver flag
            self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)

            logger.info("Browser initialized successfully")

    def fetch_page(self, url: str, wait_time: int = 3000) -> Optional[str]:
        """Fetch page content using headless browser with anti-bot measures"""
        try:
            if self.context is None:
                self.init_browser()

            page = self.context.new_page()

            try:
                logger.info(f"Fetching: {url}")

                # Navigate with shorter timeout
                page.goto(url, wait_until='domcontentloaded', timeout=15000)

                # Wait for content to load
                page.wait_for_timeout(wait_time)

                # Get content
                content = page.content()
                logger.info(f"Successfully fetched {len(content)} characters")

                return content

            except PlaywrightTimeout:
                logger.warning(f"Timeout fetching {url}")
                return None
            finally:
                page.close()

        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def extract_cs_faculty(self, cs_page_url: str) -> List[Dict]:
        """Extract faculty list from CS faculty page"""
        logger.info(f"Extracting faculty from: {cs_page_url}")

        html = self.fetch_page(cs_page_url, wait_time=5000)

        if not html:
            logger.error("Could not fetch CS faculty page")
            return []

        soup = BeautifulSoup(html, 'html.parser')
        faculty_list = []

        # Look for faculty names and profile links
        # Common patterns on Haverford pages
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            text = link.get_text(strip=True)

            # Look for user profile links
            if '/users/' in href and text and len(text.split()) >= 2:
                # Make absolute URL
                if href.startswith('/'):
                    profile_url = f"https://www.haverford.edu{href}"
                else:
                    profile_url = href

                faculty_list.append({
                    'name': text,
                    'profile_url': profile_url,
                    'department': 'Computer Science'
                })

        logger.info(f"Found {len(faculty_list)} faculty members")
        return faculty_list

    def match_with_openalex_data(self, cs_faculty: List[Dict], openalex_file: str) -> List[Dict]:
        """Match CS faculty with OpenAlex data from JSON file"""
        logger.info(f"Matching with OpenAlex data from: {openalex_file}")

        # Load OpenAlex data
        with open(openalex_file, 'r', encoding='utf-8') as f:
            openalex_data = json.load(f)

        # Create lookup by name (case-insensitive)
        openalex_lookup = {}
        for faculty in openalex_data:
            if faculty.get('openalex_id') and faculty['openalex_id'] != 'null':
                name_key = faculty['name'].lower().strip()
                openalex_lookup[name_key] = faculty

        # Match CS faculty with OpenAlex data
        matched_faculty = []
        for cs_fac in cs_faculty:
            name_key = cs_fac['name'].lower().strip()

            if name_key in openalex_lookup:
                # Merge data
                matched = {**cs_fac, **openalex_lookup[name_key]}
                matched_faculty.append(matched)
                logger.info(f"Matched: {cs_fac['name']} -> OpenAlex ID: {matched['openalex_id']}")
            else:
                logger.warning(f"No OpenAlex match for: {cs_fac['name']}")

        logger.info(f"Matched {len(matched_faculty)} faculty with OpenAlex IDs")
        return matched_faculty

    def find_cv_on_page(self, profile_url: str, faculty_name: str) -> Optional[str]:
        """Find CV link on faculty profile page"""
        logger.info(f"Searching for CV on: {profile_url}")

        html = self.fetch_page(profile_url)

        if not html:
            return None

        html_lower = html.lower()

        # Verify faculty name appears
        name_parts = faculty_name.lower().split()
        name_found = any(part in html_lower for part in name_parts if len(part) > 2)

        if not name_found:
            logger.warning(f"Faculty name '{faculty_name}' not found on profile page")
            return None

        logger.info(f"Verified '{faculty_name}' on profile page")

        # Parse HTML
        soup = BeautifulSoup(html, 'html.parser')

        # Look for CV/Resume links
        cv_keywords = ['cv', 'curriculum vitae', 'resume', 'c.v.']

        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            text = link.get_text(strip=True).lower()

            # Check if link text or href contains CV keywords
            if any(keyword in text for keyword in cv_keywords) or \
               any(keyword in href.lower() for keyword in cv_keywords):

                # Make absolute URL
                if href.startswith('/'):
                    cv_url = f"https://www.haverford.edu{href}"
                elif not href.startswith('http'):
                    cv_url = f"{profile_url.rsplit('/', 1)[0]}/{href}"
                else:
                    cv_url = href

                logger.info(f"Found CV link: {cv_url}")
                return cv_url

        logger.info("No CV link found")
        return None

    def download_cv(self, cv_url: str, faculty_name: str) -> Optional[str]:
        """Download and extract CV content"""
        logger.info(f"Downloading CV from: {cv_url}")

        # If it's a PDF, we need special handling
        if cv_url.lower().endswith('.pdf'):
            try:
                import requests
                response = requests.get(cv_url, timeout=30)
                response.raise_for_status()

                # Save PDF
                safe_name = re.sub(r'[^\w\s-]', '', faculty_name).strip().replace(' ', '_')
                pdf_path = self.cv_dir / f"{safe_name}_CV.pdf"

                with open(pdf_path, 'wb') as f:
                    f.write(response.content)

                # Extract text
                import fitz  # PyMuPDF
                doc = fitz.open(pdf_path)
                text = ""
                for page in doc:
                    text += page.get_text()
                doc.close()

                # Save text
                text_path = self.cv_dir / f"{safe_name}_CV.txt"
                with open(text_path, 'w', encoding='utf-8') as f:
                    f.write(text)

                logger.info(f"Extracted {len(text)} characters from PDF")
                return text

            except Exception as e:
                logger.error(f"Error downloading/extracting PDF: {e}")
                return None
        else:
            # Try to fetch as regular page
            html = self.fetch_page(cv_url)
            if html:
                soup = BeautifulSoup(html, 'html.parser')
                text = soup.get_text(separator='\n', strip=True)
                return text
            return None

    def filter_post_2020_content(self, cv_text: str) -> str:
        """Filter CV to only include 2020+ content"""
        if not cv_text:
            return ""

        lines = cv_text.split('\n')
        filtered_lines = []
        include_section = True

        for line in lines:
            # Look for years
            years = re.findall(r'\b(19\d{2}|20\d{2})\b', line)

            if years:
                # Check if any year is >= 2020
                recent_year = any(int(year) >= 2020 for year in years)
                if recent_year:
                    include_section = True
                elif any(int(year) < 2020 for year in years):
                    include_section = False

            # Always include headers
            if re.match(r'^[A-Z\s]{4,}$', line.strip()) or line.strip().endswith(':'):
                include_section = True

            if include_section:
                filtered_lines.append(line)

        filtered = '\n'.join(filtered_lines)
        logger.info(f"Filtered: {len(cv_text)} -> {len(filtered)} characters")
        return filtered

    def store_in_chroma(self, faculty_info: Dict, cv_content: str):
        """Store in ChromaDB"""
        logger.info(f"Storing CV for: {faculty_info['name']}")

        metadata = {
            'author': faculty_info['name'],
            'department': faculty_info.get('department', 'Computer Science'),
            'profile_url': faculty_info.get('profile_url', ''),
            'openalex_id': faculty_info.get('openalex_id', ''),
            'openalex_url': faculty_info.get('openalex_url', ''),
            'works_count': faculty_info.get('works_count', 0),
            'cited_by_count': faculty_info.get('cited_by_count', 0),
            'orcid': faculty_info.get('orcid', '') or '',
            'content_type': 'cv',
            'date': datetime.now().strftime('%Y-%m-%d')
        }

        self.chroma.add_single_submission(
            content=cv_content,
            metadata=metadata
        )

        logger.info("Successfully stored in database")

    def process_faculty(self, faculty_info: Dict) -> Dict:
        """Process one faculty member"""
        name = faculty_info['name']

        logger.info(f"\n{'='*60}")
        logger.info(f"Processing: {name}")
        logger.info(f"OpenAlex ID: {faculty_info.get('openalex_id', 'N/A')}")
        logger.info(f"Profile: {faculty_info['profile_url']}")

        result = {
            'name': name,
            'openalex_id': faculty_info.get('openalex_id'),
            'department': faculty_info.get('department', 'Computer Science'),
            'cv_found': False,
            'cv_stored': False,
            'error': None
        }

        try:
            # Find CV
            cv_url = self.find_cv_on_page(faculty_info['profile_url'], name)

            if not cv_url:
                result['error'] = 'No CV link found'
                return result

            result['cv_found'] = True
            result['cv_url'] = cv_url

            # Download
            cv_content = self.download_cv(cv_url, name)

            if not cv_content:
                result['error'] = 'Could not download CV'
                return result

            # Filter
            filtered = self.filter_post_2020_content(cv_content)

            if len(filtered) < 100:
                result['error'] = 'No substantial 2020+ content'
                return result

            # Store
            self.store_in_chroma(faculty_info, filtered)
            result['cv_stored'] = True

        except Exception as e:
            logger.error(f"Error: {e}")
            result['error'] = str(e)

        return result

    def cleanup(self):
        """Clean up browser resources"""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def run(self, cs_page_url: str = "https://www.haverford.edu/computer-science/faculty-staff"):
        """Main execution"""
        print("="*80)
        print("OPTIMIZED CV CRAWLER - CS FACULTY")
        print("="*80)
        print(f"\nTarget: {cs_page_url}")
        print("Using headless browser with anti-bot measures")
        print()

        try:
            # Step 1: Extract CS faculty
            print("Step 1: Extracting CS faculty list...")
            cs_faculty = self.extract_cs_faculty(cs_page_url)
            print(f"Found {len(cs_faculty)} CS faculty members")
            print()

            # Step 2: Match with OpenAlex data
            print("Step 2: Matching with OpenAlex data...")
            matched_faculty = self.match_with_openalex_data(
                cs_faculty,
                "haverford_faculty_with_openalex.json"
            )
            print(f"Matched {len(matched_faculty)} faculty with OpenAlex IDs")
            print()

            # Step 3: Process each faculty
            print("Step 3: Processing faculty CVs...")
            for i, faculty in enumerate(matched_faculty, 1):
                print(f"\n[{i}/{len(matched_faculty)}] {faculty['name']}")

                result = self.process_faculty(faculty)
                self.results.append(result)

                if result['cv_stored']:
                    print("  SUCCESS - CV stored in database")
                elif result['cv_found']:
                    print(f"  PARTIAL - CV found but not stored: {result['error']}")
                else:
                    print(f"  FAILED - {result['error']}")

            # Summary
            print("\n" + "="*80)
            print("SUMMARY")
            print("="*80)
            successful = sum(1 for r in self.results if r['cv_stored'])
            cvs_found = sum(1 for r in self.results if r['cv_found'])

            print(f"Total faculty processed: {len(self.results)}")
            print(f"CVs found: {cvs_found}")
            print(f"CVs stored in database: {successful}")

            # Save results
            results_file = "faculty_cv_results_cs.json"
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2)

            print(f"\nResults saved to: {results_file}")
            print()

        finally:
            self.cleanup()


if __name__ == "__main__":
    crawler = OptimizedCVCrawler()
    crawler.run()
