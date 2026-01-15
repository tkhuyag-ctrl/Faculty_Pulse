"""
Fetch Laura Been's publications from OpenAlex and add to database
Simple script to test the full pipeline with one faculty member
"""
import sys
import requests
import time
import logging
from datetime import datetime
from chroma_manager import ChromaDBManager

# Fix encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'laura_been_fetch_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


def search_faculty_openalex(name: str) -> str:
    """Search for a faculty member's OpenAlex ID by name"""
    logger.info(f"Searching OpenAlex for: {name}")

    base_url = "https://api.openalex.org"
    url = f"{base_url}/authors"

    params = {
        'search': name,
        'per_page': 5
    }

    headers = {
        'User-Agent': 'FacultyPulse/1.0 (mailto:research@example.com)'
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()
        results = data.get('results', [])

        logger.info(f"Found {len(results)} potential matches")

        for i, author in enumerate(results, 1):
            author_name = author.get('display_name', 'Unknown')
            author_id = author.get('id', '').split('/')[-1]
            works_count = author.get('works_count', 0)
            institution = 'Unknown'

            # Try to get institution
            affiliations = author.get('last_known_institutions', [])
            if affiliations:
                institution = affiliations[0].get('display_name', 'Unknown')

            logger.info(f"  {i}. {author_name} ({author_id})")
            logger.info(f"     Institution: {institution}")
            logger.info(f"     Total works: {works_count}")

            # If name matches closely and has Haverford affiliation, return this one
            if 'haverford' in institution.lower():
                logger.info(f"  ✓ Found Haverford match: {author_name}")
                return author_id

        # If no Haverford match, return first result
        if results:
            first_id = results[0].get('id', '').split('/')[-1]
            logger.warning(f"No Haverford match found. Using first result: {first_id}")
            return first_id

        logger.error("No authors found")
        return None

    except Exception as e:
        logger.error(f"Error searching OpenAlex: {e}", exc_info=True)
        return None


def fetch_publications(openalex_id: str, from_year: int = 2020):
    """Fetch publications from OpenAlex"""
    logger.info(f"Fetching publications for OpenAlex ID: {openalex_id} (from {from_year})")

    base_url = "https://api.openalex.org"
    publications = []
    page = 1
    per_page = 50

    headers = {
        'User-Agent': 'FacultyPulse/1.0 (mailto:research@example.com)'
    }

    while True:
        try:
            url = f"{base_url}/works"
            params = {
                'filter': f'author.id:{openalex_id},publication_year:{from_year}-',
                'per_page': per_page,
                'page': page,
                'sort': 'publication_date:desc'
            }

            logger.info(f"Fetching page {page}...")
            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()
            results = data.get('results', [])

            if not results:
                break

            publications.extend(results)
            logger.info(f"  Fetched {len(results)} publications from page {page}")

            # Check if there are more pages
            meta = data.get('meta', {})
            if page * per_page >= meta.get('count', 0):
                break

            page += 1
            time.sleep(0.1)  # Be polite to API

        except Exception as e:
            logger.error(f"Error fetching publications: {e}", exc_info=True)
            break

    logger.info(f"Total publications fetched: {len(publications)}")
    return publications


def format_publication_content(pub: dict, faculty_name: str, department: str, openalex_id: str) -> str:
    """Format publication into searchable document text"""

    # Extract key information
    title = pub.get('title', 'Untitled')
    pub_year = pub.get('publication_year', '')
    pub_date = pub.get('publication_date', '')

    # Get abstract
    abstract = pub.get('abstract', '')
    if not abstract:
        abstract_idx = pub.get('abstract_inverted_index', {})
        if isinstance(abstract_idx, dict) and abstract_idx:
            # Reconstruct abstract from inverted index
            max_pos = max(max(positions) for positions in abstract_idx.values())
            words = [''] * (max_pos + 1)
            for word, positions in abstract_idx.items():
                for pos in positions:
                    words[pos] = word
            abstract = ' '.join(words)

    # Authors
    authors = []
    for authorship in pub.get('authorships', [])[:10]:
        author_info = authorship.get('author', {})
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

    # Publication type
    pub_type = pub.get('type', 'article')

    # Build comprehensive content - IMPORTANT: Include faculty name throughout!
    content = f"""Faculty: {faculty_name}
Department: {department}
OpenAlex ID: {openalex_id}

Publication Title: {title}
Authors: {authors_str}
Year: {pub_year}
Publication Type: {pub_type}
Published in: {venue_name}
Citations: {cited_by_count}
"""

    if doi:
        content += f"DOI: {doi}\n"

    if pub_date:
        content += f"Date: {pub_date}\n"

    if abstract:
        content += f"\nAbstract:\n{abstract}\n"

    # Add faculty name again at the end for better retrieval
    content += f"\nThis publication is by {faculty_name} from {department}."

    return content


def add_to_database(publications, faculty_name: str, department: str, openalex_id: str):
    """Add publications to ChromaDB"""
    logger.info(f"Adding {len(publications)} publications to database for {faculty_name}")

    chroma = ChromaDBManager()

    added = 0
    failed = 0

    for i, pub in enumerate(publications, 1):
        try:
            # Format content
            content = format_publication_content(pub, faculty_name, department, openalex_id)

            # Get publication date
            pub_date = pub.get('publication_date', '') or f"{pub.get('publication_year', 2020)}-01-01"

            # Get work ID for unique submission ID
            work_id = pub.get('id', '').split('/')[-1]
            submission_id = f"pub_{openalex_id}_{work_id}" if work_id else None

            logger.info(f"  [{i}/{len(publications)}] Adding: {pub.get('title', 'Untitled')[:50]}...")

            # Add to database
            chroma.add_single_submission(
                document=content,
                faculty_name=faculty_name,
                date_published=pub_date,
                content_type='Publication',
                department=department,
                submission_id=submission_id
            )

            added += 1
            logger.info(f"    ✓ Added successfully")

        except Exception as e:
            failed += 1
            logger.error(f"    ✗ Failed to add: {str(e)}")

    logger.info(f"\nSummary: {added} added, {failed} failed")
    return added, failed


def main():
    """Main execution"""
    print("\n" + "="*80)
    print("LAURA BEEN PUBLICATION FETCHER")
    print("="*80 + "\n")

    faculty_name = "Laura Been"
    department = "Psychology"

    # Step 1: Find OpenAlex ID
    print("Step 1: Searching for Laura Been in OpenAlex...")
    openalex_id = search_faculty_openalex(faculty_name)

    if not openalex_id:
        print("✗ Could not find OpenAlex ID")
        logger.error("Failed to find OpenAlex ID")
        return

    print(f"✓ Found OpenAlex ID: {openalex_id}\n")

    # Step 2: Fetch publications
    print("Step 2: Fetching publications from OpenAlex (2020+)...")
    publications = fetch_publications(openalex_id, from_year=2020)

    if not publications:
        print("✗ No publications found")
        logger.warning("No publications found")
        return

    print(f"✓ Found {len(publications)} publications\n")

    # Display sample publications
    print("Sample publications:")
    for i, pub in enumerate(publications[:3], 1):
        print(f"  {i}. {pub.get('title', 'Untitled')[:70]}")
        print(f"     Year: {pub.get('publication_year', 'Unknown')}, Citations: {pub.get('cited_by_count', 0)}")

    if len(publications) > 3:
        print(f"  ... and {len(publications) - 3} more\n")

    # Step 3: Add to database
    print("Step 3: Adding publications to ChromaDB...")
    added, failed = add_to_database(publications, faculty_name, department, openalex_id)

    print(f"\n✓ Complete!")
    print(f"  Successfully added: {added}")
    if failed > 0:
        print(f"  Failed: {failed}")

    print("\n" + "="*80)
    print("NEXT STEPS:")
    print("="*80)
    print("1. Verify database: python inspect_database.py")
    print("2. Test retrieval: python test_retrieval.py")
    print("3. Test chatbot: streamlit run app.py")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
