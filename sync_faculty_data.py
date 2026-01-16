"""
Sync Faculty Data - Step 1 of Automation
Synchronizes faculty list from Haverford website with local JSON file
Adds new faculty, removes faculty no longer listed, updates departments
"""
import json
import logging
from datetime import datetime
from typing import List, Dict, Set
import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'faculty_sync_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)

logger = logging.getLogger(__name__)


class FacultySyncer:
    """Synchronize faculty data from Haverford website"""

    HAVERFORD_FACULTY_URL = "https://www.haverford.edu/users/faculty"
    LOCAL_FACULTY_FILE = "haverford_faculty_with_openalex.json"
    BACKUP_SUFFIX = "_backup"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def load_local_faculty(self) -> List[Dict]:
        """Load existing faculty data from local JSON"""
        logger.info(f"Loading local faculty data from {self.LOCAL_FACULTY_FILE}")
        try:
            with open(self.LOCAL_FACULTY_FILE, 'r', encoding='utf-8') as f:
                faculty = json.load(f)
            logger.info(f"Loaded {len(faculty)} faculty from local file")
            return faculty
        except FileNotFoundError:
            logger.warning(f"{self.LOCAL_FACULTY_FILE} not found, starting fresh")
            return []

    def backup_local_faculty(self):
        """Create backup of current faculty file"""
        backup_file = f"{self.LOCAL_FACULTY_FILE}{self.BACKUP_SUFFIX}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(self.LOCAL_FACULTY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Created backup: {backup_file}")
            return backup_file
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None

    def fetch_current_faculty_from_website(self) -> List[Dict]:
        """
        Fetch current faculty list from Haverford website

        Returns list of dicts with: name, department, profile_url
        """
        logger.info(f"Fetching faculty from {self.HAVERFORD_FACULTY_URL}")

        try:
            response = self.session.get(self.HAVERFORD_FACULTY_URL, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Parse faculty listings
            # NOTE: This is a placeholder - actual parsing depends on website structure
            # You'll need to inspect the HTML and update the selectors
            faculty_list = []

            # Example parsing (adjust selectors based on actual website):
            faculty_cards = soup.find_all('div', class_='faculty-card')  # Adjust selector

            for card in faculty_cards:
                try:
                    name_elem = card.find('h3')  # Adjust selector
                    dept_elem = card.find('span', class_='department')  # Adjust selector
                    profile_elem = card.find('a')  # Adjust selector

                    if name_elem:
                        faculty_list.append({
                            'name': name_elem.text.strip(),
                            'department': dept_elem.text.strip() if dept_elem else 'Unknown',
                            'profile_url': profile_elem.get('href', '') if profile_elem else ''
                        })
                except Exception as e:
                    logger.warning(f"Error parsing faculty card: {e}")
                    continue

            logger.info(f"Fetched {len(faculty_list)} faculty from website")
            return faculty_list

        except Exception as e:
            logger.error(f"Failed to fetch faculty from website: {e}")
            return []

    def match_faculty(self, website_name: str, local_faculty: List[Dict]) -> Dict:
        """
        Try to match website faculty name with local faculty entry
        Handles name variations, middle initials, etc.
        """
        # Normalize name for comparison
        website_name_norm = website_name.lower().strip().replace('.', '')

        for faculty in local_faculty:
            local_name_norm = faculty['name'].lower().strip().replace('.', '')

            # Exact match
            if website_name_norm == local_name_norm:
                return faculty

            # Check if one name is contained in the other (handles middle names)
            website_parts = set(website_name_norm.split())
            local_parts = set(local_name_norm.split())

            # If 80%+ of name parts match, consider it the same person
            if len(website_parts & local_parts) >= 0.8 * max(len(website_parts), len(local_parts)):
                return faculty

        return None

    def sync_faculty(self) -> Dict:
        """
        Main sync process:
        1. Load local faculty
        2. Fetch current faculty from website
        3. Compare and identify: new, removed, updated
        4. Merge changes
        5. Save updated file

        Returns: Dict with sync statistics
        """
        logger.info("="*80)
        logger.info("FACULTY DATA SYNCHRONIZATION")
        logger.info("="*80)

        # Step 1: Load local data
        local_faculty = self.load_local_faculty()
        local_names = {f['name'] for f in local_faculty}

        # Step 2: Backup current file
        backup_file = self.backup_local_faculty()

        # Step 3: Fetch current faculty from website
        website_faculty = self.fetch_current_faculty_from_website()

        if not website_faculty:
            logger.error("No faculty fetched from website - aborting sync")
            return {'status': 'failed', 'reason': 'website_fetch_failed'}

        website_names = {f['name'] for f in website_faculty}

        # Step 4: Identify changes
        stats = {
            'new_faculty': [],
            'removed_faculty': [],
            'updated_faculty': [],
            'unchanged_faculty': 0
        }

        # Find new faculty (on website but not in local)
        updated_faculty_list = []

        for web_faculty in website_faculty:
            matched = self.match_faculty(web_faculty['name'], local_faculty)

            if matched:
                # Faculty exists - check for updates
                updated = False
                if matched.get('department') != web_faculty['department']:
                    logger.info(f"Department change for {matched['name']}: {matched.get('department')} -> {web_faculty['department']}")
                    matched['department'] = web_faculty['department']
                    updated = True
                    stats['updated_faculty'].append(matched['name'])
                else:
                    stats['unchanged_faculty'] += 1

                updated_faculty_list.append(matched)
            else:
                # New faculty
                logger.info(f"NEW FACULTY: {web_faculty['name']} ({web_faculty['department']})")
                new_entry = {
                    'name': web_faculty['name'],
                    'department': web_faculty['department'],
                    'profile_url': web_faculty.get('profile_url', ''),
                    'openalex_id': None,  # Will be filled by OpenAlex lookup
                    'orcid': None,
                    'added_date': datetime.now().isoformat()
                }
                updated_faculty_list.append(new_entry)
                stats['new_faculty'].append(web_faculty['name'])

        # Find removed faculty (in local but not on website)
        for local_fac in local_faculty:
            matched = self.match_faculty(local_fac['name'], website_faculty)
            if not matched:
                logger.info(f"REMOVED FACULTY: {local_fac['name']} ({local_fac.get('department', 'Unknown')})")
                stats['removed_faculty'].append(local_fac['name'])

        # Step 5: Save updated faculty list
        logger.info(f"\nSaving updated faculty list ({len(updated_faculty_list)} total)")
        with open(self.LOCAL_FACULTY_FILE, 'w', encoding='utf-8') as f:
            json.dump(updated_faculty_list, f, indent=2, ensure_ascii=False)

        # Summary
        logger.info("\n" + "="*80)
        logger.info("SYNC SUMMARY")
        logger.info("="*80)
        logger.info(f"New faculty added: {len(stats['new_faculty'])}")
        for name in stats['new_faculty']:
            logger.info(f"  + {name}")
        logger.info(f"\nFaculty removed: {len(stats['removed_faculty'])}")
        for name in stats['removed_faculty']:
            logger.info(f"  - {name}")
        logger.info(f"\nFaculty updated: {len(stats['updated_faculty'])}")
        for name in stats['updated_faculty']:
            logger.info(f"  ~ {name}")
        logger.info(f"\nUnchanged faculty: {stats['unchanged_faculty']}")
        logger.info(f"\nTotal faculty after sync: {len(updated_faculty_list)}")
        logger.info(f"Backup saved: {backup_file}")

        stats['status'] = 'success'
        stats['total_faculty'] = len(updated_faculty_list)
        stats['backup_file'] = backup_file

        return stats


def main():
    """Run faculty sync"""
    syncer = FacultySyncer()
    results = syncer.sync_faculty()

    if results['status'] == 'success':
        print(f"\n✓ Faculty sync completed successfully")
        print(f"  New: {len(results['new_faculty'])}")
        print(f"  Removed: {len(results['removed_faculty'])}")
        print(f"  Updated: {len(results['updated_faculty'])}")
        print(f"  Total: {results['total_faculty']}")
    else:
        print(f"\n✗ Faculty sync failed: {results.get('reason', 'unknown')}")


if __name__ == "__main__":
    main()
