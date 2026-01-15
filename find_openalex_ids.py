"""
Find OpenAlex IDs for Haverford faculty using OpenAlex API
OpenAlex is a free, open catalog of scholarly papers, authors, institutions, and more
"""
import json
import requests
import time
import logging
from typing import Optional, Dict, List

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('openalex_search.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


def search_openalex_api(faculty_name: str, affiliation: str = "Haverford College") -> Optional[Dict]:
    """
    Search for author in OpenAlex API

    Args:
        faculty_name: Full name of faculty member
        affiliation: Institution name (default: Haverford College)

    Returns:
        Dictionary with OpenAlex ID and URL if found, None otherwise
    """
    try:
        # OpenAlex API endpoint for authors
        base_url = "https://api.openalex.org/authors"

        # OpenAlex requires polite pool - add email in User-Agent
        headers = {
            'User-Agent': 'mailto:research@example.com',
            'Accept': 'application/json'
        }

        # Clean up name
        clean_name = faculty_name.strip()

        # Simple search by name only
        params = {
            'search': clean_name,
            'per_page': 10  # Get more results to check
        }

        logger.info(f"Searching OpenAlex for: {faculty_name}")

        response = requests.get(base_url, params=params, headers=headers, timeout=10)

        if response.status_code == 429:
            # Rate limited
            logger.warning("Rate limited by OpenAlex API, waiting 2 seconds...")
            time.sleep(2)
            return None

        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])

            # Look for Haverford in affiliations of results
            for result in results:
                # Check affiliations history
                affiliations = result.get('affiliations', [])
                last_institution = result.get('last_known_institutions', [])

                # Check if Haverford is in affiliations or last_known_institutions
                has_haverford = False

                # Check last known
                if last_institution:
                    for inst in last_institution:
                        if inst and 'haverford' in inst.get('display_name', '').lower():
                            has_haverford = True
                            break

                # Check affiliation history
                if not has_haverford and affiliations:
                    for aff in affiliations:
                        inst = aff.get('institution', {})
                        if inst and 'haverford' in inst.get('display_name', '').lower():
                            has_haverford = True
                            break

                if has_haverford:
                    openalex_id = result.get('id', '')
                    display_name = result.get('display_name', '')
                    works_count = result.get('works_count', 0)
                    cited_by_count = result.get('cited_by_count', 0)

                    if openalex_id.startswith('https://openalex.org/'):
                        short_id = openalex_id.replace('https://openalex.org/', '')
                    else:
                        short_id = openalex_id

                    logger.info(f"  Found: {display_name} ({short_id}) - {works_count} works, {cited_by_count} citations")

                    return {
                        'openalex_id': short_id,
                        'openalex_url': openalex_id,
                        'display_name': display_name,
                        'works_count': works_count,
                        'cited_by_count': cited_by_count
                    }

        logger.info(f"  No OpenAlex ID found for {faculty_name}")
        return None

    except Exception as e:
        logger.error(f"Failed to search OpenAlex for {faculty_name}: {e}")
        return None


def main():
    """Main execution"""
    print("="*80)
    print("OPENALEX ID FINDER")
    print("="*80)

    # Load faculty data
    input_file = "haverford_faculty_with_orcid.json"

    print(f"\nLoading faculty from: {input_file}")

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            faculty_list = json.load(f)
    except Exception as e:
        print(f"Error loading file: {e}")
        return

    print(f"Loaded {len(faculty_list)} faculty members")
    print("\nSearching OpenAlex database...")
    print("Note: OpenAlex is free and open - no authentication needed!")
    print()

    found_count = 0
    total_works = 0
    total_citations = 0

    for i, faculty in enumerate(faculty_list, 1):
        name = faculty['name']
        dept = faculty['department']

        # Encode-safe printing for Windows console
        # Use ascii encoding with xmlcharrefreplace to avoid cp1252 codec issues
        safe_name = name.encode('ascii', errors='replace').decode('ascii')
        safe_dept = dept.encode('ascii', errors='replace').decode('ascii')
        try:
            print(f"[{i}/{len(faculty_list)}] {name} ({dept})...", end=" ", flush=True)
        except UnicodeEncodeError:
            print(f"[{i}/{len(faculty_list)}] {safe_name} ({safe_dept})...", end=" ", flush=True)

        # Search for OpenAlex ID
        result = search_openalex_api(name)

        if result:
            faculty['openalex_id'] = result['openalex_id']
            faculty['openalex_url'] = result['openalex_url']
            faculty['openalex_display_name'] = result['display_name']
            faculty['works_count'] = result['works_count']
            faculty['cited_by_count'] = result['cited_by_count']

            found_count += 1
            total_works += result['works_count']
            total_citations += result['cited_by_count']

            print(f"Found! {result['openalex_id']} ({result['works_count']} works)")
        else:
            faculty['openalex_id'] = None
            faculty['openalex_url'] = None
            faculty['openalex_display_name'] = None
            faculty['works_count'] = 0
            faculty['cited_by_count'] = 0
            print("Not found")

        # Rate limiting - be polite to the API
        time.sleep(0.2)  # 5 requests per second max

    # Save updated data
    output_file = "haverford_faculty_with_openalex.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(faculty_list, f, indent=2, ensure_ascii=False)

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total faculty: {len(faculty_list)}")
    print(f"With OpenAlex ID: {found_count}")
    print(f"Without OpenAlex ID: {len(faculty_list) - found_count}")
    print(f"Coverage: {found_count/len(faculty_list)*100:.1f}%")
    print(f"\nAggregate Statistics:")
    print(f"  Total works: {total_works:,}")
    print(f"  Total citations: {total_citations:,}")
    if found_count > 0:
        print(f"  Average works per faculty: {total_works/found_count:.1f}")
        print(f"  Average citations per faculty: {total_citations/found_count:.1f}")
    print(f"\nSaved to: {output_file}")
    print("="*80)

    # Show some examples
    if found_count > 0:
        print("\nTop 10 faculty by works count:")
        sorted_faculty = sorted([f for f in faculty_list if f.get('openalex_id')],
                               key=lambda x: x.get('works_count', 0),
                               reverse=True)
        for i, f in enumerate(sorted_faculty[:10], 1):
            print(f"  {i}. {f['name']} ({f['department']}): {f['works_count']} works, {f['cited_by_count']:,} citations")
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
