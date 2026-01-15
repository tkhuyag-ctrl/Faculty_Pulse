"""
CV Crawler with OpenAlex Integration
- Crawl faculty pages from CS faculty-staff page
- Find and download CVs (PDFs)
- Extract data from CVs (only post-2020)
- Link to OpenAlex API IDs
- Store in ChromaDB
"""
import os
import re
import json
import logging
import requests
from datetime import datetime
from typing import Optional, Dict, List
from bs4 import BeautifulSoup
from smart_fetcher import SmartFetcher
from chroma_manager import ChromaDBManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('cv_crawler.log')
    ]
)

logger = logging.getLogger(__name__)


class OpenAlexAPI:
    """Interface to OpenAlex API for faculty identification"""

    BASE_URL = "https://api.openalex.org"

    def __init__(self, email: Optional[str] = None):
        """
        Initialize OpenAlex API

        Args:
            email: Your email for polite pool (faster rate limits)
        """
        self.email = email
        self.session = requests.Session()
        if email:
            self.session.headers.update({'User-Agent': f'mailto:{email}'})

    def search_author(self, name: str, institution: str = "Haverford") -> Optional[Dict]:
        """
        Search for an author by name and institution

        Args:
            name: Faculty member's name
            institution: Institution name

        Returns:
            Author info with OpenAlex ID, or None if not found
        """
        try:
            # Clean name for search
            search_name = name.replace('.', '').strip()

            # Search endpoint
            url = f"{self.BASE_URL}/authors"
            params = {
                'search': f'{search_name} {institution}'
            }

            logger.info(f"Searching OpenAlex for: {search_name}")
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            if data['results']:
                # Take the first (best) match
                author = data['results'][0]

                return {
                    'openalex_id': author['id'],
                    'display_name': author['display_name'],
                    'orcid': author.get('orcid'),
                    'works_count': author.get('works_count', 0),
                    'cited_by_count': author.get('cited_by_count', 0),
                    'last_known_institution': author.get('last_known_institution', {}).get('display_name')
                }

            logger.warning(f"No OpenAlex match found for: {name}")
            return None

        except Exception as e:
            logger.error(f"OpenAlex API error for {name}: {e}")
            return None

    def get_recent_works(self, openalex_id: str, from_year: int = 2020) -> List[Dict]:
        """
        Get recent works for an author

        Args:
            openalex_id: OpenAlex author ID
            from_year: Only get works from this year onwards

        Returns:
            List of work metadata
        """
        try:
            url = f"{self.BASE_URL}/works"
            params = {
                'filter': f'author.id:{openalex_id},publication_year:>{from_year-1}',
                'per-page': 50
            }

            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            works = []
            for work in data['results']:
                works.append({
                    'title': work.get('title'),
                    'publication_year': work.get('publication_year'),
                    'doi': work.get('doi'),
                    'type': work.get('type'),
                    'cited_by_count': work.get('cited_by_count', 0)
                })

            logger.info(f"Found {len(works)} recent works for {openalex_id}")
            return works

        except Exception as e:
            logger.error(f"Error fetching works: {e}")
            return []


class CVCrawler:
    """Crawl faculty CVs and extract relevant data"""

    def __init__(self, openalex_email: Optional[str] = None):
        self.fetcher = SmartFetcher(delay_range=(3.0, 5.0))
        self.openalex = OpenAlexAPI(email=openalex_email)
        self.db = ChromaDBManager()

        # Directory for storing CVs
        self.cv_dir = "./faculty_cvs"
        os.makedirs(self.cv_dir, exist_ok=True)

    def extract_faculty_from_page(self, url: str) -> List[Dict]:
        """
        Extract faculty information from department page

        Args:
            url: Department faculty page URL

        Returns:
            List of faculty with names and profile URLs
        """
        logger.info(f"Extracting faculty from: {url}")

        # Initialize Playwright for this page
        self.fetcher._init_playwright()
        page = self.fetcher.playwright_context.new_page()

        try:
            page.goto(url, wait_until='load', timeout=90000)
            page.wait_for_timeout(5000)
            html = page.content()
        finally:
            page.close()

        soup = BeautifulSoup(html, 'html.parser')

        # Find faculty links
        faculty_list = []

        # Look for profile links
        profile_links = soup.find_all('a', href=re.compile(r'/users/'))

        seen_names = set()
        for link in profile_links:
            name = link.get_text(strip=True)
            href = link.get('href', '')

            if not name or len(name.split()) < 2:
                continue

            if name in seen_names:
                continue
            seen_names.add(name)

            # Make full URL
            if href.startswith('/'):
                profile_url = f"https://www.haverford.edu{href}"
            else:
                profile_url = href

            faculty_list.append({
                'name': name,
                'profile_url': profile_url
            })

            logger.info(f"Found faculty: {name}")

        return faculty_list

    def find_cv_on_page(self, profile_url: str) -> Optional[str]:
        """
        Find CV/Resume link on faculty profile page

        Args:
            profile_url: Faculty profile URL

        Returns:
            CV URL if found, None otherwise
        """
        logger.info(f"Looking for CV on: {profile_url}")

        result = self.fetcher.fetch(profile_url)
        if not result['success']:
            return None

        # Re-fetch as HTML to find links
        self.fetcher._init_playwright()
        page = self.fetcher.playwright_context.new_page()

        try:
            page.goto(profile_url, wait_until='load', timeout=60000)
            page.wait_for_timeout(3000)
            html = page.content()
        except:
            logger.warning(f"Could not load page: {profile_url}")
            return None
        finally:
            page.close()

        soup = BeautifulSoup(html, 'html.parser')

        # Look for CV/Resume links
        cv_patterns = [
            re.compile(r'cv', re.I),
            re.compile(r'curriculum\s+vitae', re.I),
            re.compile(r'resume', re.I),
            re.compile(r'vita', re.I)
        ]

        for pattern in cv_patterns:
            # Look in link text
            cv_link = soup.find('a', string=pattern)
            if cv_link and cv_link.get('href'):
                href = cv_link['href']
                if href.startswith('http'):
                    return href
                elif href.startswith('/'):
                    return f"https://www.haverford.edu{href}"

            # Look in href
            cv_link = soup.find('a', href=pattern)
            if cv_link:
                href = cv_link['href']
                if href.startswith('http'):
                    return href
                elif href.startswith('/'):
                    return f"https://www.haverford.edu{href}"

        # Look for PDF links (might be CV)
        pdf_links = soup.find_all('a', href=re.compile(r'\.pdf$', re.I))
        for link in pdf_links:
            text = link.get_text().lower()
            if any(word in text for word in ['cv', 'vita', 'resume']):
                href = link['href']
                if href.startswith('http'):
                    return href
                elif href.startswith('/'):
                    return f"https://www.haverford.edu{href}"

        logger.info(f"No CV found on: {profile_url}")
        return None

    def download_cv(self, cv_url: str, faculty_name: str) -> Optional[str]:
        """
        Download CV PDF

        Args:
            cv_url: URL to CV
            faculty_name: Faculty member's name

        Returns:
            Path to downloaded CV, or None if failed
        """
        try:
            logger.info(f"Downloading CV from: {cv_url}")

            response = self.fetcher.session.get(cv_url, timeout=30)
            response.raise_for_status()

            # Save to file
            safe_name = re.sub(r'[^\w\s-]', '', faculty_name).strip().replace(' ', '_')
            filename = f"{safe_name}_CV.pdf"
            filepath = os.path.join(self.cv_dir, filename)

            with open(filepath, 'wb') as f:
                f.write(response.content)

            logger.info(f"Saved CV to: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Error downloading CV: {e}")
            return None

    def extract_text_from_cv(self, cv_path: str) -> Optional[str]:
        """
        Extract text from CV PDF

        Args:
            cv_path: Path to CV PDF file

        Returns:
            Extracted text, or None if failed
        """
        try:
            import pypdf

            with open(cv_path, 'rb') as f:
                pdf = pypdf.PdfReader(f)
                text = ""
                for page in pdf.pages:
                    text += page.extract_text()

            logger.info(f"Extracted {len(text)} characters from CV")
            return text

        except Exception as e:
            logger.error(f"Error extracting CV text: {e}")

            # Try PyMuPDF as fallback
            try:
                import fitz

                doc = fitz.open(cv_path)
                text = ""
                for page in doc:
                    text += page.get_text()
                doc.close()

                logger.info(f"Extracted {len(text)} characters from CV (PyMuPDF)")
                return text

            except Exception as e2:
                logger.error(f"PyMuPDF also failed: {e2}")
                return None

    def filter_post_2020_content(self, cv_text: str) -> str:
        """
        Filter CV content to only include entries from 2020 onwards

        Args:
            cv_text: Full CV text

        Returns:
            Filtered text with only 2020+ content
        """
        # This is a heuristic approach
        # Look for year patterns and keep sections with 2020+

        lines = cv_text.split('\n')
        filtered_lines = []
        current_year = None

        for line in lines:
            # Look for year in line
            year_match = re.search(r'\b(20[2-9]\d)\b', line)
            if year_match:
                current_year = int(year_match.group(1))

            # If we have a recent year context, include the line
            if current_year and current_year >= 2020:
                filtered_lines.append(line)
            # Also include lines that don't have years (might be titles, descriptions)
            elif not re.search(r'\b(19\d{2}|20[01]\d)\b', line):
                # No old years found, might be relevant
                filtered_lines.append(line)

        return '\n'.join(filtered_lines)

    def process_faculty(self, faculty_info: Dict) -> Dict:
        """
        Process a single faculty member: find OpenAlex ID, get CV, extract data

        Args:
            faculty_info: Dictionary with name and profile_url

        Returns:
            Complete faculty record with CV data and OpenAlex ID
        """
        name = faculty_info['name']
        profile_url = faculty_info['profile_url']

        logger.info(f"\n{'='*80}")
        logger.info(f"Processing: {name}")
        logger.info(f"{'='*80}")

        # Step 1: Get OpenAlex ID
        openalex_data = self.openalex.search_author(name, "Haverford")

        if not openalex_data:
            logger.warning(f"No OpenAlex ID found for {name}, skipping")
            return None

        logger.info(f"OpenAlex ID: {openalex_data['openalex_id']}")
        logger.info(f"ORCID: {openalex_data.get('orcid', 'N/A')}")

        # Step 2: Find CV on profile page
        cv_url = self.find_cv_on_page(profile_url)

        cv_data = None
        if cv_url:
            # Step 3: Download CV
            cv_path = self.download_cv(cv_url, name)

            if cv_path:
                # Step 4: Extract text
                cv_text = self.extract_text_from_cv(cv_path)

                if cv_text:
                    # Step 5: Filter to post-2020
                    filtered_text = self.filter_post_2020_content(cv_text)

                    if filtered_text and len(filtered_text) > 100:
                        cv_data = {
                            'cv_path': cv_path,
                            'cv_url': cv_url,
                            'full_text': cv_text,
                            'filtered_text_2020plus': filtered_text
                        }
                        logger.info(f"CV extracted: {len(filtered_text)} characters (2020+)")
                    else:
                        logger.warning(f"No relevant 2020+ content found in CV")
        else:
            logger.info(f"No CV found on profile page")

        # Step 6: Get recent works from OpenAlex as backup
        recent_works = self.openalex.get_recent_works(openalex_data['openalex_id'])

        return {
            'name': name,
            'profile_url': profile_url,
            'openalex': openalex_data,
            'cv': cv_data,
            'recent_works': recent_works
        }

    def store_in_database(self, faculty_record: Dict):
        """
        Store faculty CV data in ChromaDB

        Args:
            faculty_record: Complete faculty record with CV and OpenAlex data
        """
        if not faculty_record:
            return

        name = faculty_record['name']

        # Store CV data if available
        if faculty_record['cv'] and faculty_record['cv']['filtered_text_2020plus']:
            submission_id = f"cv_{faculty_record['openalex']['openalex_id'].split('/')[-1]}"

            self.db.add_single_submission(
                document=faculty_record['cv']['filtered_text_2020plus'],
                faculty_name=name,
                date_published=datetime.now().isoformat(),
                content_type="CV",
                department="Computer Science",
                submission_id=submission_id
            )

            logger.info(f"Stored CV data for {name} in database")

        # Store recent works metadata
        for work in faculty_record['recent_works']:
            if work['title']:
                work_id = f"work_{faculty_record['openalex']['openalex_id'].split('/')[-1]}_{work['publication_year']}_{len(work['title'])}"

                work_text = f"Title: {work['title']}\nYear: {work['publication_year']}\nType: {work['type']}\nDOI: {work.get('doi', 'N/A')}\nCited by: {work['cited_by_count']}"

                self.db.add_single_submission(
                    document=work_text,
                    faculty_name=name,
                    date_published=f"{work['publication_year']}-01-01T00:00:00Z",
                    content_type="Publication",
                    department="Computer Science",
                    submission_id=work_id
                )

        if faculty_record['recent_works']:
            logger.info(f"Stored {len(faculty_record['recent_works'])} recent works for {name}")

    def crawl_cs_faculty(self):
        """Main method to crawl CS faculty page and process all faculty"""
        cs_faculty_url = "https://www.haverford.edu/computer-science/faculty-staff"

        print("="*80)
        print("CV CRAWLER WITH OPENALEX INTEGRATION")
        print("="*80)
        print(f"\nTarget: {cs_faculty_url}")
        print("This will:")
        print("  1. Extract faculty from CS page")
        print("  2. Find OpenAlex IDs for each faculty")
        print("  3. Download and extract CVs")
        print("  4. Filter for 2020+ content")
        print("  5. Store in ChromaDB")
        print()

        # Step 1: Get faculty list
        print("Step 1: Extracting faculty list...")
        faculty_list = self.extract_faculty_from_page(cs_faculty_url)
        print(f"Found {len(faculty_list)} faculty members\n")

        # Step 2: Process each faculty
        results = []
        for i, faculty in enumerate(faculty_list, 1):
            print(f"\n[{i}/{len(faculty_list)}] Processing {faculty['name']}...")

            try:
                result = self.process_faculty(faculty)
                if result:
                    results.append(result)

                    # Store in database
                    self.store_in_database(result)

            except Exception as e:
                logger.error(f"Error processing {faculty['name']}: {e}")
                import traceback
                traceback.print_exc()

        # Summary
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        print(f"Total faculty processed: {len(results)}")
        print(f"With OpenAlex IDs: {len([r for r in results if r['openalex']])}")
        print(f"With CVs downloaded: {len([r for r in results if r['cv']])}")
        print(f"With 2020+ CV data: {len([r for r in results if r['cv'] and r['cv']['filtered_text_2020plus']])}")

        # Save results to JSON
        with open('faculty_cv_results.json', 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\nResults saved to: faculty_cv_results.json")
        print(f"CVs saved to: {self.cv_dir}/")

    def close(self):
        """Clean up resources"""
        self.fetcher.close()


if __name__ == "__main__":
    # Optional: Set your email for OpenAlex polite pool
    openalex_email = os.environ.get('OPENALEX_EMAIL', None)

    crawler = CVCrawler(openalex_email=openalex_email)

    try:
        crawler.crawl_cs_faculty()
    finally:
        crawler.close()
