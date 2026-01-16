"""
Auto Update Publications - Step 2 of Automation
Automatically fetches new publications from OpenAlex for all faculty
Only adds publications not already in the database
"""
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Set
import requests
from chroma_manager import ChromaDBManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'auto_update_pubs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)

logger = logging.getLogger(__name__)


class AutoPublicationUpdater:
    """Automatically update publications from OpenAlex"""

    def __init__(self, chroma_db_path: str = "./chroma_db"):
        self.chroma = ChromaDBManager(persist_directory=chroma_db_path)
        self.base_url = "https://api.openalex.org"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'FacultyPulse/2.0 (mailto:research@haverford.edu)',
            'Accept': 'application/json'
        })
        self.existing_work_ids = set()

    def load_existing_publications(self):
        """Load existing publication work IDs from ChromaDB"""
        logger.info("Loading existing publications from database...")
        try:
            all_docs = self.chroma.collection.get(include=['metadatas'])
            if all_docs and 'metadatas' in all_docs:
                for metadata in all_docs['metadatas']:
                    if metadata.get('content_type') == 'Publication':
                        work_id = metadata.get('openalex_work_id', '')
                        if work_id:
                            self.existing_work_ids.add(work_id)
            logger.info(f"Found {len(self.existing_work_ids)} existing publications")
        except Exception as e:
            logger.warning(f"Could not load existing publications: {e}")

    def load_faculty_with_openalex(self) -> List[Dict]:
        """Load faculty who have OpenAlex IDs"""
        logger.info("Loading faculty data...")
        try:
            with open('haverford_faculty_with_openalex.json', 'r', encoding='utf-8') as f:
                all_faculty = json.load(f)

            valid_faculty = [
                f for f in all_faculty
                if f.get('openalex_id') and
                   f['openalex_id'] != 'null' and
                   f.get('department') and
                   f.get('department') != 'Unknown'
            ]

            logger.info(f"Found {len(valid_faculty)} faculty with OpenAlex IDs and known departments")
            return valid_faculty
        except Exception as e:
            logger.error(f"Failed to load faculty: {e}")
            return []

    def fetch_recent_publications(self, openalex_id: str, days_back: int = 60) -> List[Dict]:
        """
        Fetch recent publications from OpenAlex

        Args:
            openalex_id: OpenAlex author ID
            days_back: How many days back to check for new publications

        Returns:
            List of publication dictionaries
        """
        # Calculate date threshold
        date_threshold = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

        if openalex_id.startswith('http'):
            openalex_id = openalex_id.split('/')[-1]

        logger.info(f"Fetching publications since {date_threshold} for {openalex_id}")

        publications = []
        page = 1
        per_page = 100

        try:
            while True:
                url = f"{self.base_url}/works"
                params = {
                    'filter': f'authorships.author.id:{openalex_id},from_publication_date:{date_threshold}',
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

        except Exception as e:
            logger.error(f"Error fetching publications: {e}")

        logger.info(f"Total fetched: {len(publications)} publications")
        return publications

    def reconstruct_abstract(self, inverted_index: Dict) -> str:
        """Reconstruct abstract from OpenAlex inverted index"""
        if not inverted_index or not isinstance(inverted_index, dict):
            return ""

        try:
            max_pos = 0
            for positions in inverted_index.values():
                if positions:
                    max_pos = max(max_pos, max(positions))

            words = [''] * (max_pos + 1)
            for word, positions in inverted_index.items():
                for pos in positions:
                    words[pos] = word

            return ' '.join(words).strip()
        except Exception as e:
            logger.warning(f"Error reconstructing abstract: {e}")
            return ""

    def format_publication(self, pub: Dict, faculty_info: Dict) -> Dict:
        """Format publication for ChromaDB storage"""
        work_id = pub.get('id', '')
        title = pub.get('title', 'Untitled')
        pub_year = pub.get('publication_year')
        pub_date = pub.get('publication_date', '')

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

        # Venue
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

        # Build content
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

    def store_new_publications(self, publications: List[Dict], faculty_info: Dict) -> Dict:
        """
        Store new publications in ChromaDB (skip duplicates)

        Returns: Dict with statistics
        """
        stats = {
            'new': 0,
            'skipped': 0,
            'errors': 0
        }

        for pub in publications:
            try:
                work_id = pub.get('id', '')

                # Skip if already exists
                if work_id in self.existing_work_ids:
                    stats['skipped'] += 1
                    continue

                formatted = self.format_publication(pub, faculty_info)
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

                stats['new'] += 1
                self.existing_work_ids.add(work_id)

            except Exception as e:
                logger.error(f"Error storing publication: {e}")
                stats['errors'] += 1

        return stats

    def update_all_faculty(self, days_back: int = 60) -> Dict:
        """
        Update publications for all faculty

        Args:
            days_back: How many days back to check for new publications (default: 60 = ~2 months)

        Returns:
            Dict with update statistics
        """
        logger.info("="*80)
        logger.info("AUTOMATED PUBLICATION UPDATE")
        logger.info("="*80)
        logger.info(f"Checking for new publications from last {days_back} days")
        logger.info("")

        # Load existing publications
        self.load_existing_publications()

        # Load faculty
        faculty_list = self.load_faculty_with_openalex()

        if not faculty_list:
            logger.error("No faculty found!")
            return {'status': 'failed', 'reason': 'no_faculty'}

        # Statistics
        overall_stats = {
            'faculty_processed': 0,
            'total_new': 0,
            'total_skipped': 0,
            'total_errors': 0,
            'faculty_with_new': [],
            'faculty_without_new': []
        }

        # Process each faculty
        for i, faculty in enumerate(faculty_list, 1):
            name = faculty['name']
            openalex_id = faculty['openalex_id']

            logger.info(f"\n[{i}/{len(faculty_list)}] {name} ({faculty['department']})")

            try:
                # Fetch recent publications
                publications = self.fetch_recent_publications(openalex_id, days_back=days_back)

                if publications:
                    # Store new ones
                    stats = self.store_new_publications(publications, faculty)

                    overall_stats['faculty_processed'] += 1
                    overall_stats['total_new'] += stats['new']
                    overall_stats['total_skipped'] += stats['skipped']
                    overall_stats['total_errors'] += stats['errors']

                    if stats['new'] > 0:
                        logger.info(f"  ✓ Added {stats['new']} new publication(s)")
                        overall_stats['faculty_with_new'].append({
                            'name': name,
                            'new_count': stats['new']
                        })
                    else:
                        logger.info(f"  - No new publications (all {stats['skipped']} already in database)")
                        overall_stats['faculty_without_new'].append(name)
                else:
                    logger.info(f"  - No publications found in last {days_back} days")
                    overall_stats['faculty_without_new'].append(name)
                    overall_stats['faculty_processed'] += 1

            except Exception as e:
                logger.error(f"  ✗ Error processing {name}: {e}")
                overall_stats['total_errors'] += 1

        # Summary
        logger.info("\n" + "="*80)
        logger.info("UPDATE SUMMARY")
        logger.info("="*80)
        logger.info(f"Faculty processed: {overall_stats['faculty_processed']}/{len(faculty_list)}")
        logger.info(f"New publications added: {overall_stats['total_new']}")
        logger.info(f"Duplicates skipped: {overall_stats['total_skipped']}")
        logger.info(f"Errors: {overall_stats['total_errors']}")

        if overall_stats['faculty_with_new']:
            logger.info(f"\nFaculty with new publications ({len(overall_stats['faculty_with_new'])}):")
            for fac in overall_stats['faculty_with_new']:
                logger.info(f"  + {fac['name']}: {fac['new_count']} new")

        logger.info(f"\nTotal publications in database: {len(self.existing_work_ids)}")

        overall_stats['status'] = 'success'
        return overall_stats


def main():
    """Run automated publication update"""
    updater = AutoPublicationUpdater()

    # Default: check last 60 days (good for bi-weekly runs)
    results = updater.update_all_faculty(days_back=60)

    if results['status'] == 'success':
        print(f"\n✓ Publication update completed successfully")
        print(f"  New publications: {results['total_new']}")
        print(f"  Faculty with updates: {len(results['faculty_with_new'])}")
        print(f"  Total in database: {len(updater.existing_work_ids)}")
    else:
        print(f"\n✗ Publication update failed: {results.get('reason', 'unknown')}")


if __name__ == "__main__":
    main()
