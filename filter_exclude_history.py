"""
Filter faculty with OpenAlex IDs and fetch their publications from 2020 onwards
EXCLUDES History department faculty
"""
import json
import requests
import time
import logging
from typing import List, Dict, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('filter_research_no_history.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


def fetch_recent_publications(openalex_id: str, from_year: int = 2020) -> List[Dict]:
    """
    Fetch publications from OpenAlex API for a given author ID, filtered by year

    Args:
        openalex_id: OpenAlex author ID (e.g., A5051964527)
        from_year: Only fetch publications from this year onwards (default: 2020)

    Returns:
        List of publication dictionaries with title, year, DOI, citations, etc.
    """
    try:
        # OpenAlex API endpoint for works by author
        base_url = "https://api.openalex.org/works"

        headers = {
            'User-Agent': 'mailto:research@example.com',
            'Accept': 'application/json'
        }

        # Build filter query
        # Filter by author ID and publication year >= 2020
        params = {
            'filter': f'author.id:{openalex_id},from_publication_date:{from_year}-01-01',
            'per_page': 200,  # Maximum allowed
            'sort': 'publication_date:desc'
        }

        logger.info(f"Fetching publications for {openalex_id} (from {from_year}+)")

        response = requests.get(base_url, params=params, headers=headers, timeout=15)

        if response.status_code == 429:
            logger.warning("Rate limited by OpenAlex API, waiting 2 seconds...")
            time.sleep(2)
            return []

        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])

            publications = []
            for work in results:
                pub = {
                    'id': work.get('id', '').replace('https://openalex.org/', ''),
                    'title': work.get('title', ''),
                    'publication_year': work.get('publication_year'),
                    'publication_date': work.get('publication_date'),
                    'doi': work.get('doi'),
                    'type': work.get('type'),
                    'cited_by_count': work.get('cited_by_count', 0),
                    'is_open_access': work.get('open_access', {}).get('is_oa', False),
                    'primary_location': work.get('primary_location', {}).get('source', {}).get('display_name'),
                    'abstract': work.get('abstract_inverted_index') is not None
                }
                publications.append(pub)

            logger.info(f"  Found {len(publications)} publications from {from_year}+")
            return publications

        else:
            logger.error(f"OpenAlex API returned status {response.status_code}")
            return []

    except Exception as e:
        logger.error(f"Failed to fetch publications for {openalex_id}: {e}")
        return []


def main():
    """Main execution"""
    print("="*80)
    print("FILTER FACULTY & FETCH RECENT RESEARCH (2020+)")
    print("EXCLUDING HISTORY DEPARTMENT")
    print("="*80)

    # Load faculty data
    input_file = "haverford_faculty_with_openalex.json"

    print(f"\nLoading faculty from: {input_file}")

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            faculty_list = json.load(f)
    except Exception as e:
        print(f"Error loading file: {e}")
        return

    print(f"Loaded {len(faculty_list)} total faculty members")

    # Filter 1: Keep only faculty with OpenAlex IDs
    faculty_with_openalex = [f for f in faculty_list if f.get('openalex_id')]

    print(f"After OpenAlex ID filter: {len(faculty_with_openalex)} faculty")

    # Filter 2: EXCLUDE History department
    faculty_filtered = [f for f in faculty_with_openalex if f.get('department', '').lower() != 'history']

    history_excluded = len(faculty_with_openalex) - len(faculty_filtered)

    print(f"After excluding History: {len(faculty_filtered)} faculty")
    print(f"Removed {len(faculty_list) - len(faculty_filtered)} total faculty:")
    print(f"  - {len(faculty_list) - len(faculty_with_openalex)} without OpenAlex ID")
    print(f"  - {history_excluded} from History department")

    print("\n" + "="*80)
    print("FETCHING RECENT PUBLICATIONS (2020+)")
    print("="*80)
    print()

    total_publications = 0
    faculty_with_recent_pubs = 0

    for i, faculty in enumerate(faculty_filtered, 1):
        name = faculty['name']
        dept = faculty['department']
        openalex_id = faculty['openalex_id']

        # Safe printing for Windows console
        safe_name = name.encode('ascii', errors='replace').decode('ascii')
        safe_dept = dept.encode('ascii', errors='replace').decode('ascii')

        try:
            print(f"[{i}/{len(faculty_filtered)}] {name} ({dept})...", end=" ", flush=True)
        except UnicodeEncodeError:
            print(f"[{i}/{len(faculty_filtered)}] {safe_name} ({safe_dept})...", end=" ", flush=True)

        # Fetch recent publications (2020+)
        publications = fetch_recent_publications(openalex_id, from_year=2020)

        faculty['publications_2020_plus'] = publications
        faculty['recent_publications_count'] = len(publications)

        if publications:
            faculty_with_recent_pubs += 1
            total_publications += len(publications)
            print(f"{len(publications)} publications")
        else:
            print("No recent publications")

        # Rate limiting - be polite to the API
        time.sleep(0.3)  # ~3 requests per second

    # Save filtered data with publications
    output_file = "haverford_faculty_filtered_no_history.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(faculty_filtered, f, indent=2, ensure_ascii=False)

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Original faculty count: {len(faculty_list)}")
    print(f"Faculty with OpenAlex ID: {len(faculty_with_openalex)}")
    print(f"History department excluded: {history_excluded}")
    print(f"Final filtered count: {len(faculty_filtered)}")
    print(f"Total removed: {len(faculty_list) - len(faculty_filtered)}")
    print()
    print(f"Faculty with publications (2020+): {faculty_with_recent_pubs}")
    print(f"Total publications (2020+): {total_publications}")
    if faculty_with_recent_pubs > 0:
        print(f"Average publications per faculty: {total_publications/faculty_with_recent_pubs:.1f}")
    print()
    print(f"Saved to: {output_file}")
    print("="*80)

    # Show top 10 most productive faculty (2020+)
    if total_publications > 0:
        print("\nTop 10 most productive faculty (2020+):")
        sorted_faculty = sorted(faculty_filtered,
                               key=lambda x: x.get('recent_publications_count', 0),
                               reverse=True)

        for i, f in enumerate(sorted_faculty[:10], 1):
            pub_count = f.get('recent_publications_count', 0)
            if pub_count > 0:
                safe_name = f['name'].encode('ascii', errors='replace').decode('ascii')
                safe_dept = f['department'].encode('ascii', errors='replace').decode('ascii')
                try:
                    print(f"  {i}. {f['name']} ({f['department']}): {pub_count} publications")
                    print(f"     {f['openalex_url']}")
                except UnicodeEncodeError:
                    print(f"  {i}. {safe_name} ({safe_dept}): {pub_count} publications")
                    print(f"     {f['openalex_url']}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
