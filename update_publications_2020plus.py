"""
Enhanced OpenAlex Publications Updater
- Uses existing OpenAlex IDs from faculty JSON
- Fetches ALL publications from 2020+ (with complete dates & PDFs)
- Only includes faculty with known departments
- Continues from where database left off
"""
import json
import logging
import time
import requests
from datetime import datetime
from typing import List, Dict, Optional
from chroma_manager import ChromaDBManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'publications_update_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)

logger = logging.getLogger(__name__)


class PublicationsUpdater:
    """Enhanced publications updater with full date/PDF extraction"""

    # Haverford College institution ID in OpenAlex
    HAVERFORD_INSTITUTION_ID = "I201448701"

    def __init__(self, chroma_db_path: str = "./chroma_db"):
        self.chroma = ChromaDBManager(persist_directory=chroma_db_path)
        self.base_url = "https://api.openalex.org"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'FacultyPulse/2.0 (mailto:research@haverford.edu)',
            'Accept': 'application/json'
        })
        self.results = []
        self.existing_work_ids = set()

    def load_existing_publications(self):
        """Load existing publication IDs from ChromaDB to avoid duplicates"""
        logger.info("Loading existing publications from database...")
        try:
            all_docs = self.chroma.get_all_submissions()
            if all_docs and 'metadatas' in all_docs:
                for metadata in all_docs['metadatas']:
                    if metadata.get('content_type') == 'Publication':
                        work_id = metadata.get('openalex_work_id', '')
                        if work_id:
                            self.existing_work_ids.add(work_id)
            logger.info(f"Found {len(self.existing_work_ids)} existing publications")
        except Exception as e:
            logger.warning(f"Could not load existing publications: {e}")

    def load_faculty_with_departments(self, json_file: str) -> List[Dict]:
        """Load faculty who have OpenAlex IDs AND known departments"""
        logger.info(f"Loading faculty data from: {json_file}")

        with open(json_file, 'r', encoding='utf-8') as f:
            all_faculty = json.load(f)

        # Filter for faculty with OpenAlex IDs AND known departments
        valid_faculty = []
        for f in all_faculty:
            dept = f.get('department', '')
            openalex_id = f.get('openalex_id')

            # Must have OpenAlex ID, department, and department != "Unknown"
            if openalex_id and openalex_id != 'null' and dept and dept != 'Unknown':
                valid_faculty.append(f)

        logger.info(f"Found {len(valid_faculty)} faculty with OpenAlex IDs and known departments")

        # Show department breakdown
        dept_counts = {}
        for f in valid_faculty:
            dept = f['department']
            dept_counts[dept] = dept_counts.get(dept, 0) + 1

        logger.info("Department breakdown:")
        for dept, count in sorted(dept_counts.items()):
            logger.info(f"  {dept}: {count} faculty")

        return valid_faculty

    def fetch_publications_enhanced(self, openalex_id: str, from_year: int = 2020) -> List[Dict]:
        """
        Fetch publications with enhanced data extraction

        Returns full work objects with:
        - Complete publication dates
        - PDF links (open_access.oa_url)
        - Full abstract
        - All metadata
        """
        # Extract just the ID part if full URL provided
        if openalex_id.startswith('http'):
            openalex_id = openalex_id.split('/')[-1]

        logger.info(f"Fetching publications for {openalex_id} (from {from_year})")

        publications = []
        page = 1
        per_page = 100  # Increased for efficiency

        while True:
            try:
                url = f"{self.base_url}/works"
                params = {
                    'filter': f'authorships.author.id:{openalex_id},publication_year:{from_year}-,institutions.id:{self.HAVERFORD_INSTITUTION_ID}',
                    'per_page': per_page,
                    'page': page,
                    'sort': 'publication_date:desc',
                    'select': 'id,title,publication_date,publication_year,authorships,primary_location,open_access,abstract_inverted_index,doi,cited_by_count,type,biblio'
                }

                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()

                data = response.json()
                results = data.get('results', [])

                if not results:
                    break

                publications.extend(results)
                logger.info(f"  Page {page}: {len(results)} publications")

                # Check if there are more pages
                meta = data.get('meta', {})
                if page * per_page >= meta.get('count', 0):
                    break

                page += 1
                time.sleep(0.1)  # Rate limiting

            except Exception as e:
                logger.error(f"Error fetching publications: {e}")
                break

        logger.info(f"Total: {len(publications)} publications")
        return publications

    def reconstruct_abstract(self, inverted_index: Dict) -> str:
        """Reconstruct abstract from OpenAlex inverted index"""
        if not inverted_index or not isinstance(inverted_index, dict):
            return ""

        try:
            # Find max position
            max_pos = 0
            for positions in inverted_index.values():
                if positions:
                    max_pos = max(max_pos, max(positions))

            # Create word array
            words = [''] * (max_pos + 1)
            for word, positions in inverted_index.items():
                for pos in positions:
                    words[pos] = word

            return ' '.join(words).strip()
        except Exception as e:
            logger.warning(f"Error reconstructing abstract: {e}")
            return ""

    def format_publication_enhanced(self, pub: Dict, faculty_info: Dict) -> Dict:
        """Format publication with enhanced data extraction"""

        # Basic info
        work_id = pub.get('id', '')
        title = pub.get('title', 'Untitled')
        pub_year = pub.get('publication_year')
        pub_date = pub.get('publication_date', '')  # Full date: YYYY-MM-DD

        # Abstract
        abstract_inverted = pub.get('abstract_inverted_index', {})
        abstract = self.reconstruct_abstract(abstract_inverted)

        # Authors
        authors = []
        for authorship in pub.get('authorships', [])[:15]:
            author = authorship.get('author', {})
            if author.get('display_name'):
                authors.append(author['display_name'])
        authors_str = ', '.join(authors) if authors else 'Unknown'

        # Publication venue
        primary_location = pub.get('primary_location', {})
        source = primary_location.get('source', {})
        venue_name = source.get('display_name', 'Unknown venue')
        venue_type = source.get('type', '')

        # PDF/Open Access
        open_access = pub.get('open_access', {})
        is_oa = open_access.get('is_oa', False)
        oa_url = open_access.get('oa_url', '')
        pdf_url = primary_location.get('pdf_url', '') or oa_url

        # DOI
        doi = pub.get('doi', '')
        if doi and doi.startswith('https://doi.org/'):
            doi = doi.replace('https://doi.org/', '')

        # Citations
        cited_by_count = pub.get('cited_by_count', 0)

        # Publication type
        pub_type = pub.get('type', 'article')

        # Build rich content for ChromaDB
        content_parts = [
            f"Faculty: {faculty_info['name']}",
            f"Department: {faculty_info['department']}",
            f"OpenAlex ID: {faculty_info.get('openalex_id', '')}",
            "",
            f"Publication Title: {title}",
            f"Authors: {authors_str}",
            f"Year: {pub_year}",
        ]

        if pub_date:
            content_parts.append(f"Publication Date: {pub_date}")

        content_parts.append(f"Publication Type: {pub_type}")
        content_parts.append(f"Published in: {venue_name}")

        if venue_type:
            content_parts.append(f"Venue Type: {venue_type}")

        if doi:
            content_parts.append(f"DOI: {doi}")

        if pdf_url:
            content_parts.append(f"PDF/Open Access: {pdf_url}")

        if abstract:
            content_parts.append(f"\nAbstract: {abstract}")

        content_parts.append(f"\nCitations: {cited_by_count}")
        content_parts.append(f"OpenAlex Work ID: {work_id}")

        content = '\n'.join(content_parts)

        # Metadata
        metadata = {
            'faculty_name': faculty_info['name'],
            'department': faculty_info['department'],
            'content_type': 'Publication',
            'date_published': pub_date or f"{pub_year}-01-01" if pub_year else '',
            'openalex_work_id': work_id,
            'openalex_author_id': faculty_info.get('openalex_id', ''),
            'title': title[:500],
            'year': str(pub_year) if pub_year else '',
            'venue': venue_name[:200],
            'doi': doi,
            'pdf_url': pdf_url,
            'is_open_access': str(is_oa),
            'cited_by_count': cited_by_count,
            'publication_type': pub_type
        }

        return {
            'content': content,
            'metadata': metadata,
            'work_id': work_id
        }

    def store_publications(self, publications: List[Dict], faculty_info: Dict) -> int:
        """Store publications in ChromaDB (skip duplicates)"""
        logger.info(f"Storing publications for {faculty_info['name']}")

        stored = 0
        skipped = 0

        for pub in publications:
            try:
                formatted = self.format_publication_enhanced(pub, faculty_info)
                work_id = formatted['work_id']

                # Skip if already in database
                if work_id in self.existing_work_ids:
                    skipped += 1
                    continue

                metadata = formatted['metadata']

                # Generate unique ID
                submission_id = f"pub_{metadata['openalex_author_id']}_{work_id.split('/')[-1]}"

                self.chroma.add_single_submission(
                    document=formatted['content'],
                    faculty_name=metadata['faculty_name'],
                    date_published=metadata['date_published'],
                    content_type='Publication',
                    department=metadata['department'],
                    submission_id=submission_id
                )

                stored += 1
                self.existing_work_ids.add(work_id)

            except Exception as e:
                logger.error(f"Error storing publication: {e}")

        logger.info(f"Stored: {stored}, Skipped (duplicates): {skipped}")
        return stored

    def process_faculty(self, faculty_info: Dict) -> Dict:
        """Process one faculty member"""
        name = faculty_info['name']
        openalex_id = faculty_info['openalex_id']
        department = faculty_info['department']

        logger.info(f"\n{'='*80}")
        logger.info(f"Processing: {name}")
        logger.info(f"Department: {department}")
        logger.info(f"OpenAlex ID: {openalex_id}")

        result = {
            'name': name,
            'department': department,
            'openalex_id': openalex_id,
            'publications_fetched': 0,
            'publications_stored': 0,
            'error': None
        }

        try:
            publications = self.fetch_publications_enhanced(openalex_id, from_year=2020)
            result['publications_fetched'] = len(publications)

            if publications:
                stored = self.store_publications(publications, faculty_info)
                result['publications_stored'] = stored
            else:
                logger.info(f"No publications found since 2020")

        except Exception as e:
            logger.error(f"Error processing {name}: {e}")
            result['error'] = str(e)

        return result

    def run(self, json_file: str = "haverford_faculty_with_openalex.json"):
        """Main execution"""
        print("="*80)
        print("ENHANCED OPENALEX PUBLICATIONS UPDATER")
        print("="*80)
        print(f"\nHaverford Institution ID: {self.HAVERFORD_INSTITUTION_ID}")
        print("Filter: Faculty with OpenAlex IDs and known departments")
        print("Date range: 2020 onwards")
        print("Features: Complete dates, PDF links, full abstracts")
        print()

        # Load existing publications
        self.load_existing_publications()

        # Load faculty
        faculty_list = self.load_faculty_with_departments(json_file)

        if not faculty_list:
            print("No faculty with OpenAlex IDs and departments found!")
            return

        print(f"\nProcessing {len(faculty_list)} faculty members...")
        print()

        # Process each faculty
        for i, faculty in enumerate(faculty_list, 1):
            print(f"[{i}/{len(faculty_list)}] {faculty['name']} ({faculty['department']})")

            result = self.process_faculty(faculty)
            self.results.append(result)

            if result['publications_stored'] > 0:
                print(f"  ✓ Stored {result['publications_stored']} new publications")
            elif result['publications_fetched'] > 0:
                print(f"  = All {result['publications_fetched']} publications already in database")
            else:
                print(f"  - No publications found")

            # Small delay between faculty
            time.sleep(0.2)

        # Summary
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        total_fetched = sum(r['publications_fetched'] for r in self.results)
        total_stored = sum(r['publications_stored'] for r in self.results)

        print(f"Faculty processed: {len(self.results)}")
        print(f"Publications fetched: {total_fetched}")
        print(f"New publications stored: {total_stored}")
        print(f"Total publications in database: {len(self.existing_work_ids)}")
        print()

        # Save results
        results_file = f"publications_update_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'faculty_processed': len(self.results),
                'publications_fetched': total_fetched,
                'publications_stored': total_stored,
                'results': self.results
            }, f, indent=2)

        print(f"Results saved to: {results_file}")


if __name__ == "__main__":
    updater = PublicationsUpdater()
    updater.run()
