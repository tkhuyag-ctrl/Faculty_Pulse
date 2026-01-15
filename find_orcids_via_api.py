"""
Find ORCID identifiers for Haverford faculty using ORCID public API
This avoids 403 errors by using the official ORCID search API
"""
import json
import requests
import time
import logging
from typing import Optional, Dict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('orcid_search.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


def search_orcid_api(faculty_name: str, affiliation: str = "Haverford College") -> Optional[str]:
    """
    Search for ORCID using the official ORCID public API

    Args:
        faculty_name: Full name of faculty member
        affiliation: Institution name (default: Haverford College)

    Returns:
        ORCID identifier if found, None otherwise
    """
    try:
        # ORCID public API endpoint
        base_url = "https://pub.orcid.org/v3.0/search/"

        # Build search query
        # Format: given-names:FirstName AND family-name:LastName AND affiliation-org-name:Haverford
        name_parts = faculty_name.split()

        if len(name_parts) < 2:
            logger.warning(f"Insufficient name parts for: {faculty_name}")
            return None

        # Handle titles and prefixes
        titles = ['dr.', 'prof.', 'dr', 'prof', 'mr.', 'mrs.', 'ms.']
        clean_parts = [part for part in name_parts if part.lower() not in titles]

        if len(clean_parts) < 2:
            clean_parts = name_parts

        # Try different name combinations
        queries = []

        # Strategy 1: First name + Last name
        if len(clean_parts) >= 2:
            first_name = clean_parts[0]
            last_name = clean_parts[-1]
            queries.append(f'given-names:{first_name} AND family-name:{last_name}')

        # Strategy 2: Full name search with affiliation
        queries.append(f'"{faculty_name}" AND affiliation-org-name:Haverford')

        # Strategy 3: Family name only with affiliation
        if len(clean_parts) >= 2:
            last_name = clean_parts[-1]
            queries.append(f'family-name:{last_name} AND affiliation-org-name:Haverford')

        headers = {
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (compatible; FacultyPulse/1.0; mailto:research@example.com)'
        }

        for query in queries:
            try:
                logger.info(f"Searching ORCID for: {faculty_name} with query: {query}")

                params = {
                    'q': query
                }

                response = requests.get(base_url, params=params, headers=headers, timeout=10)

                if response.status_code == 200:
                    data = response.json()

                    # Check if we found results
                    num_found = data.get('num-found', 0)

                    if num_found > 0:
                        # Get the first result
                        results = data.get('result', [])
                        if results:
                            orcid_path = results[0].get('orcid-identifier', {}).get('path')
                            if orcid_path:
                                logger.info(f"Found ORCID for {faculty_name}: {orcid_path}")
                                return orcid_path

                elif response.status_code == 429:
                    # Rate limited - wait and retry
                    logger.warning("Rate limited by ORCID API, waiting 5 seconds...")
                    time.sleep(5)
                    continue

                else:
                    logger.warning(f"ORCID API returned status {response.status_code}")

                # Small delay between queries
                time.sleep(0.5)

            except Exception as e:
                logger.error(f"Error querying ORCID API: {e}")
                continue

        logger.info(f"No ORCID found for {faculty_name}")
        return None

    except Exception as e:
        logger.error(f"Failed to search ORCID for {faculty_name}: {e}")
        return None


def main():
    """Main execution"""
    print("="*80)
    print("ORCID FINDER VIA PUBLIC API")
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
    print("\nSearching ORCID database...")
    print("Note: This uses the official ORCID public API (no 403 errors!)")
    print()

    found_count = 0

    for i, faculty in enumerate(faculty_list, 1):
        name = faculty['name']
        dept = faculty['department']

        print(f"[{i}/{len(faculty_list)}] {name} ({dept})...", end=" ")

        # Search for ORCID
        orcid = search_orcid_api(name)

        if orcid:
            faculty['orcid'] = orcid
            found_count += 1
            print(f"ORCID: {orcid}")
        else:
            print("Not found")

        # Rate limiting - be respectful to ORCID API
        time.sleep(1)

    # Save updated data
    output_file = "haverford_faculty_with_orcid.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(faculty_list, f, indent=2, ensure_ascii=False)

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total faculty: {len(faculty_list)}")
    print(f"With ORCID: {found_count}")
    print(f"Without ORCID: {len(faculty_list) - found_count}")
    print(f"Coverage: {found_count/len(faculty_list)*100:.1f}%")
    print(f"\nSaved to: {output_file}")
    print("="*80)

    # Show some examples of found ORCIDs
    if found_count > 0:
        print("\nExamples of faculty with ORCID:")
        count = 0
        for faculty in faculty_list:
            if faculty['orcid']:
                print(f"  {faculty['name']} ({faculty['department']}): {faculty['orcid']}")
                count += 1
                if count >= 10:
                    break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
