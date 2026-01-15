"""
CV Crawler using Local OpenAlex Data
- Load faculty with OpenAlex IDs from haverford_faculty_with_openalex.json
- Find and download CVs from profile URLs
- Extract data from CVs (only post-2020)
- Store in ChromaDB with faculty info
"""
import os
import re
import json
import logging
from datetime import datetime
from typing import Optional, Dict, List
from pathlib import Path
from smart_fetcher import SmartFetcher
from chroma_manager import ChromaDBManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('cv_crawler_local.log')
    ]
)

logger = logging.getLogger(__name__)


class CVCrawlerLocal:
    """Crawl and extract CVs using local faculty data with OpenAlex IDs"""

    def __init__(self, cv_dir: str = "./faculty_cvs"):
        self.fetcher = SmartFetcher()
        self.chroma = ChromaDBManager()
        self.cv_dir = Path(cv_dir)
        self.cv_dir.mkdir(exist_ok=True)

        self.results = []

    def load_faculty_data(self, json_file: str) -> List[Dict]:
        """Load faculty data from JSON file, filter for those with OpenAlex IDs"""
        logger.info(f"Loading faculty data from: {json_file}")

        with open(json_file, 'r', encoding='utf-8') as f:
            all_faculty = json.load(f)

        # Filter for faculty with OpenAlex IDs
        faculty_with_openalex = [
            f for f in all_faculty
            if f.get('openalex_id') and f.get('openalex_id') != 'null'
        ]

        logger.info(f"Found {len(faculty_with_openalex)} faculty members with OpenAlex IDs out of {len(all_faculty)} total")
        return faculty_with_openalex

    def find_cv_on_page(self, profile_url: str, faculty_name: str) -> Optional[str]:
        """
        Look for CV/Resume link on faculty profile page
        Verify the faculty name appears on the page
        """
        logger.info(f"Searching for CV on: {profile_url}")

        # Fetch the profile page
        result = self.fetcher.fetch(profile_url)

        if not result['success']:
            logger.warning(f"Could not fetch profile page: {result.get('error')}")
            return None

        content = result['content']

        # Verify faculty name appears on the page
        # Check for both full name and parts of the name
        name_parts = faculty_name.lower().split()
        name_found = False

        for part in name_parts:
            if len(part) > 2 and part in content.lower():  # Avoid checking very short parts
                name_found = True
                break

        if not name_found:
            logger.warning(f"Faculty name '{faculty_name}' not found on profile page, skipping")
            return None

        logger.info(f"Verified faculty name '{faculty_name}' appears on profile page")

        # Look for CV/Resume links
        cv_patterns = [
            r'(https?://[^\s<>"\']+(?:cv|resume|curriculum[_\-]vitae)[^\s<>"\']*\.pdf)',
            r'(https?://[^\s<>"\']+\.pdf)',  # Any PDF might be a CV
            r'href=["\']([^"\']+(?:cv|resume|curriculum[_\-]vitae)[^"\']*)["\']',
        ]

        for pattern in cv_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                cv_url = matches[0]
                # Make absolute URL if relative
                if cv_url.startswith('/'):
                    from urllib.parse import urljoin
                    cv_url = urljoin(profile_url, cv_url)
                logger.info(f"Found CV link: {cv_url}")
                return cv_url

        logger.info("No CV link found on profile page")
        return None

    def download_cv(self, cv_url: str, faculty_name: str) -> Optional[str]:
        """Download CV PDF and save to disk"""
        logger.info(f"Downloading CV from: {cv_url}")

        # Create safe filename
        safe_name = re.sub(r'[^\w\s-]', '', faculty_name).strip().replace(' ', '_')
        cv_path = self.cv_dir / f"{safe_name}_CV.pdf"

        # Download
        result = self.fetcher.fetch(cv_url)

        if not result['success']:
            logger.warning(f"Could not download CV: {result.get('error')}")
            return None

        # For PDFs, the fetcher extracts text automatically
        # Save the extracted text
        text_path = self.cv_dir / f"{safe_name}_CV.txt"
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(result['content'])

        logger.info(f"Saved CV text to: {text_path}")
        return result['content']

    def filter_post_2020_content(self, cv_text: str) -> str:
        """
        Filter CV content to only include entries from 2020 onwards
        Look for year patterns and filter sections
        """
        if not cv_text:
            return ""

        lines = cv_text.split('\n')
        filtered_lines = []
        current_section_year = None
        include_line = True

        for line in lines:
            # Look for year patterns (2020-2026)
            year_match = re.search(r'\b(202[0-6])\b', line)

            if year_match:
                year = int(year_match.group(1))
                current_section_year = year
                include_line = (year >= 2020)

            # Include headers and section titles regardless
            if re.match(r'^[A-Z\s]{3,}$', line.strip()) or line.strip().endswith(':'):
                include_line = True

            # If we found a year >= 2020, or no year pattern yet, include
            if include_line or current_section_year is None or current_section_year >= 2020:
                filtered_lines.append(line)

        filtered_content = '\n'.join(filtered_lines)

        # Log filtering stats
        original_chars = len(cv_text)
        filtered_chars = len(filtered_content)
        logger.info(f"Filtered CV content: {original_chars} -> {filtered_chars} characters")

        return filtered_content

    def store_in_chroma(self, faculty_info: Dict, cv_content: str):
        """Store faculty CV data in ChromaDB"""
        logger.info(f"Storing CV data for: {faculty_info['name']}")

        # Prepare metadata
        metadata = {
            'author': faculty_info['name'],
            'department': faculty_info.get('department', 'Unknown'),
            'profile_url': faculty_info.get('profile_url', ''),
            'openalex_id': faculty_info.get('openalex_id', ''),
            'openalex_url': faculty_info.get('openalex_url', ''),
            'works_count': faculty_info.get('works_count', 0),
            'cited_by_count': faculty_info.get('cited_by_count', 0),
            'orcid': faculty_info.get('orcid', '') or '',
            'content_type': 'cv',
            'date': datetime.now().strftime('%Y-%m-%d')
        }

        # Add to ChromaDB
        self.chroma.add_single_submission(
            content=cv_content,
            metadata=metadata
        )

        logger.info(f"Successfully stored CV for {faculty_info['name']}")

    def process_faculty(self, faculty_info: Dict) -> Dict:
        """Process a single faculty member: find CV, download, filter, store"""
        name = faculty_info['name']
        profile_url = faculty_info['profile_url']
        openalex_id = faculty_info['openalex_id']

        logger.info(f"\nProcessing: {name}")
        logger.info(f"  OpenAlex ID: {openalex_id}")
        logger.info(f"  Profile: {profile_url}")

        result = {
            'name': name,
            'openalex_id': openalex_id,
            'department': faculty_info.get('department', 'Unknown'),
            'cv_found': False,
            'cv_downloaded': False,
            'cv_stored': False,
            'error': None
        }

        try:
            # Step 1: Find CV on profile page (with name verification)
            cv_url = self.find_cv_on_page(profile_url, name)

            if not cv_url:
                result['error'] = 'No CV link found on profile'
                return result

            result['cv_found'] = True
            result['cv_url'] = cv_url

            # Step 2: Download CV
            cv_content = self.download_cv(cv_url, name)

            if not cv_content:
                result['error'] = 'Could not download CV'
                return result

            result['cv_downloaded'] = True

            # Step 3: Filter for 2020+ content
            filtered_content = self.filter_post_2020_content(cv_content)

            if not filtered_content or len(filtered_content) < 100:
                result['error'] = 'No substantial 2020+ content found'
                return result

            # Step 4: Store in ChromaDB
            self.store_in_chroma(faculty_info, filtered_content)
            result['cv_stored'] = True

        except Exception as e:
            logger.error(f"Error processing {name}: {e}")
            result['error'] = str(e)

        return result

    def run(self, json_file: str = "haverford_faculty_with_openalex.json"):
        """Main execution: process all faculty with OpenAlex IDs"""

        print("="*80)
        print("CV CRAWLER WITH LOCAL OPENALEX DATA")
        print("="*80)
        print(f"\nLoading faculty from: {json_file}")
        print("This will:")
        print("  1. Load faculty with OpenAlex IDs")
        print("  2. Visit profile URLs and verify name appears")
        print("  3. Find and download CVs")
        print("  4. Filter for 2020+ content")
        print("  5. Store in ChromaDB")
        print()

        # Load faculty data
        faculty_list = self.load_faculty_data(json_file)

        print(f"Found {len(faculty_list)} faculty members with OpenAlex IDs")
        print()

        # Process each faculty member
        for i, faculty in enumerate(faculty_list, 1):
            print(f"\n[{i}/{len(faculty_list)}] Processing {faculty['name']}...")

            result = self.process_faculty(faculty)
            self.results.append(result)

            # Log result
            if result['cv_stored']:
                print(f"  SUCCESS: CV stored in database")
            elif result['cv_found']:
                print(f"  PARTIAL: CV found but not stored - {result.get('error')}")
            else:
                print(f"  FAILED: {result.get('error')}")

        # Summary
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        successful = sum(1 for r in self.results if r['cv_stored'])
        cvs_found = sum(1 for r in self.results if r['cv_found'])

        print(f"Total faculty processed: {len(self.results)}")
        print(f"CVs found: {cvs_found}")
        print(f"CVs downloaded and stored: {successful}")
        print()

        # Save detailed results
        results_file = "faculty_cv_results_local.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2)

        print(f"Detailed results saved to: {results_file}")
        print(f"CVs saved to: {self.cv_dir}/")
        print()


if __name__ == "__main__":
    crawler = CVCrawlerLocal()
    crawler.run()
