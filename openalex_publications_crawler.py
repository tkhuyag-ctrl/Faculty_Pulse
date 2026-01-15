"""
OpenAlex Publications Crawler
- Load CS faculty with OpenAlex IDs from local data
- Fetch publications from OpenAlex API (2020+)
- Store in ChromaDB with faculty metadata
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
        logging.FileHandler('openalex_publications.log')
    ]
)

logger = logging.getLogger(__name__)


class OpenAlexPublicationsCrawler:
    """Fetch publications from OpenAlex for faculty with OpenAlex IDs"""

    def __init__(self):
        self.chroma = ChromaDBManager()
        self.base_url = "https://api.openalex.org"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'FacultyPulse/1.0 (mailto:research@example.com)'
        })
        self.results = []

    def load_cs_faculty_with_openalex(self, json_file: str) -> List[Dict]:
        """Load CS faculty who have OpenAlex IDs"""
        logger.info(f"Loading faculty data from: {json_file}")

        with open(json_file, 'r', encoding='utf-8') as f:
            all_faculty = json.load(f)

        # Filter for CS faculty with OpenAlex IDs
        cs_faculty = [
            f for f in all_faculty
            if f.get('department') == 'Computer Science' and
               f.get('openalex_id') and
               f['openalex_id'] != 'null'
        ]

        logger.info(f"Found {len(cs_faculty)} CS faculty with OpenAlex IDs")
        return cs_faculty

    def fetch_publications(self, openalex_id: str, from_year: int = 2020) -> List[Dict]:
        """
        Fetch publications for a faculty member from OpenAlex

        Args:
            openalex_id: OpenAlex author ID (e.g., "A5015357170")
            from_year: Only fetch publications from this year onwards

        Returns:
            List of publication dictionaries
        """
        # Extract just the ID part if full URL provided
        if openalex_id.startswith('http'):
            openalex_id = openalex_id.split('/')[-1]

        logger.info(f"Fetching publications for OpenAlex ID: {openalex_id} (from {from_year})")

        publications = []
        page = 1
        per_page = 50  # Max allowed by OpenAlex

        while True:
            try:
                # Build query
                url = f"{self.base_url}/works"
                params = {
                    'filter': f'author.id:{openalex_id},publication_year:{from_year}-',
                    'per_page': per_page,
                    'page': page,
                    'sort': 'publication_date:desc'
                }

                logger.info(f"Fetching page {page}...")
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()

                data = response.json()
                results = data.get('results', [])

                if not results:
                    break

                publications.extend(results)
                logger.info(f"Fetched {len(results)} publications from page {page}")

                # Check if there are more pages
                meta = data.get('meta', {})
                if page * per_page >= meta.get('count', 0):
                    break

                page += 1
                time.sleep(0.1)  # Be polite to API

            except Exception as e:
                logger.error(f"Error fetching publications: {e}")
                break

        logger.info(f"Total publications fetched: {len(publications)}")
        return publications

    def format_publication(self, pub: Dict, faculty_info: Dict) -> Dict:
        """Format publication data for storage"""
        # Extract key information
        title = pub.get('title', 'Untitled')
        pub_year = pub.get('publication_year')
        pub_date = pub.get('publication_date', '')

        # Get abstract/summary
        abstract = pub.get('abstract', '')
        if not abstract:
            abstract = pub.get('abstract_inverted_index', '')
            if isinstance(abstract, dict):
                # Reconstruct abstract from inverted index
                words = [''] * (max(max(positions) for positions in abstract.values()) + 1 if abstract else 0)
                for word, positions in abstract.items():
                    for pos in positions:
                        words[pos] = word
                abstract = ' '.join(words)

        # Authors
        authors = []
        for author in pub.get('authorships', [])[:10]:  # Limit to first 10
            author_info = author.get('author', {})
            if author_info.get('display_name'):
                authors.append(author_info['display_name'])

        authors_str = ', '.join(authors) if authors else 'Unknown'

        # Venue
        venue = pub.get('primary_location', {}).get('source', {})
        venue_name = venue.get('display_name', 'Unknown venue')

        # DOI
        doi = pub.get('doi', '')

        # Citations
        cited_by_count = pub.get('cited_by_count', 0)

        # Build content text for ChromaDB
        content_parts = [
            f"Title: {title}",
            f"Authors: {authors_str}",
            f"Year: {pub_year}",
            f"Published in: {venue_name}",
        ]

        if doi:
            content_parts.append(f"DOI: {doi}")

        if abstract:
            content_parts.append(f"\nAbstract: {abstract}")

        content_parts.append(f"\nCitations: {cited_by_count}")

        content = '\n'.join(content_parts)

        # Metadata for ChromaDB
        metadata = {
            'author': faculty_info['name'],
            'department': faculty_info.get('department', 'Computer Science'),
            'openalex_id': faculty_info.get('openalex_id', ''),
            'orcid': faculty_info.get('orcid', '') or '',
            'title': title[:500],  # Limit length for metadata
            'year': str(pub_year) if pub_year else '',
            'date': pub_date,
            'venue': venue_name[:200],
            'doi': doi,
            'cited_by_count': cited_by_count,
            'content_type': 'publication',
            'openalex_work_id': pub.get('id', '')
        }

        return {
            'content': content,
            'metadata': metadata
        }

    def store_publications(self, publications: List[Dict], faculty_info: Dict) -> int:
        """Store publications in ChromaDB"""
        logger.info(f"Storing {len(publications)} publications for {faculty_info['name']}")

        stored = 0
        for pub in publications:
            try:
                formatted = self.format_publication(pub, faculty_info)
                metadata = formatted['metadata']

                # Use ChromaDB's expected parameters
                self.chroma.add_single_submission(
                    document=formatted['content'],
                    faculty_name=metadata['author'],
                    date_published=metadata.get('date', ''),
                    content_type='Publication',
                    department=metadata['department'],
                    submission_id=None  # Let Chroma autogenerate
                )
                stored += 1
            except Exception as e:
                logger.error(f"Error storing publication: {e}")

        logger.info(f"Successfully stored {stored} publications")
        return stored

    def process_faculty(self, faculty_info: Dict) -> Dict:
        """Process one faculty member: fetch and store publications"""
        name = faculty_info['name']
        openalex_id = faculty_info['openalex_id']

        logger.info(f"\n{'='*60}")
        logger.info(f"Processing: {name}")
        logger.info(f"OpenAlex ID: {openalex_id}")

        result = {
            'name': name,
            'openalex_id': openalex_id,
            'department': faculty_info.get('department', 'Computer Science'),
            'publications_fetched': 0,
            'publications_stored': 0,
            'error': None
        }

        try:
            # Fetch publications
            publications = self.fetch_publications(openalex_id, from_year=2020)
            result['publications_fetched'] = len(publications)

            if publications:
                # Store in ChromaDB
                stored = self.store_publications(publications, faculty_info)
                result['publications_stored'] = stored
            else:
                logger.warning(f"No publications found for {name} since 2020")

        except Exception as e:
            logger.error(f"Error processing {name}: {e}")
            result['error'] = str(e)

        return result

    def run(self, json_file: str = "haverford_faculty_with_openalex.json"):
        """Main execution"""
        print("="*80)
        print("OPENALEX PUBLICATIONS CRAWLER")
        print("="*80)
        print("\nFetching publications from OpenAlex API")
        print("Filter: Computer Science faculty with OpenAlex IDs")
        print("Date range: 2020 onwards")
        print()

        # Load faculty
        faculty_list = self.load_cs_faculty_with_openalex(json_file)

        if not faculty_list:
            print("No CS faculty with OpenAlex IDs found!")
            return

        print(f"Found {len(faculty_list)} CS faculty with OpenAlex IDs")
        print()

        # Process each faculty
        for i, faculty in enumerate(faculty_list, 1):
            print(f"\n[{i}/{len(faculty_list)}] {faculty['name']}")

            result = self.process_faculty(faculty)
            self.results.append(result)

            if result['publications_stored'] > 0:
                print(f"  SUCCESS: {result['publications_stored']} publications stored")
            elif result['publications_fetched'] > 0:
                print(f"  PARTIAL: {result['publications_fetched']} fetched but not stored")
            else:
                print(f"  NO PUBLICATIONS: {result.get('error', 'None found since 2020')}")

        # Summary
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        total_fetched = sum(r['publications_fetched'] for r in self.results)
        total_stored = sum(r['publications_stored'] for r in self.results)

        print(f"Faculty processed: {len(self.results)}")
        print(f"Total publications fetched: {total_fetched}")
        print(f"Total publications stored: {total_stored}")
        print()

        # Save results
        results_file = "openalex_publications_results.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2)

        print(f"Results saved to: {results_file}")
        print()


if __name__ == "__main__":
    crawler = OpenAlexPublicationsCrawler()
    crawler.run()
