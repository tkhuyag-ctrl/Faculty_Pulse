"""
Fetch awards and talks for Haverford faculty from OpenAlex
OpenAlex doesn't have direct "awards" or "talks" endpoints, but we can:
1. Get grants/funding from works metadata
2. Get conference proceedings (talks/presentations)
3. Check for awards mentioned in abstracts
"""
import sys
import json
import requests
import time
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Haverford College OpenAlex Institution ID
HAVERFORD_INSTITUTION_ID = "I79424937"

def fetch_haverford_works(work_type=None, from_year=2020):
    """
    Fetch works from Haverford faculty

    Args:
        work_type: Filter by type (e.g., 'proceedings-article' for conference talks)
        from_year: Filter by year
    """
    all_works = []
    page = 1
    per_page = 200

    headers = {
        'User-Agent': 'FacultyPulse/1.0 (mailto:research@example.com)'
    }

    print(f"\nFetching works from Haverford College...")
    print(f"Institution ID: {HAVERFORD_INSTITUTION_ID}")
    if work_type:
        print(f"Type filter: {work_type}")
    print(f"Year filter: {from_year}+\n")

    while True:
        try:
            url = "https://api.openalex.org/works"

            filters = [
                f'institutions.id:{HAVERFORD_INSTITUTION_ID}',
                f'publication_year:{from_year}-'
            ]

            if work_type:
                filters.append(f'type:{work_type}')

            params = {
                'filter': ','.join(filters),
                'per_page': per_page,
                'page': page,
                'sort': 'publication_date:desc'
            }

            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()
            results = data.get('results', [])

            if not results:
                break

            all_works.extend(results)

            meta = data.get('meta', {})
            total_count = meta.get('count', 0)

            print(f"  Page {page}: {len(results)} works (total so far: {len(all_works)}/{total_count})")

            if page * per_page >= total_count:
                break

            page += 1
            time.sleep(0.1)  # Be polite to API

        except Exception as e:
            print(f"  Error on page {page}: {e}")
            break

    return all_works


def categorize_works(works):
    """Categorize works by type"""
    categories = {}

    for work in works:
        work_type = work.get('type', 'unknown')
        if work_type not in categories:
            categories[work_type] = []
        categories[work_type].append(work)

    return categories


def extract_grants_and_awards(works):
    """Extract grants and awards from works metadata"""
    grants_info = []

    for work in works:
        # Check for grants in work metadata
        grants = work.get('grants', [])
        if grants:
            for grant in grants:
                grants_info.append({
                    'work_title': work.get('title', 'Untitled'),
                    'work_id': work.get('id', ''),
                    'funder': grant.get('funder', ''),
                    'award_id': grant.get('award_id', '')
                })

    return grants_info


def main():
    print("\n" + "="*80)
    print("HAVERFORD FACULTY AWARDS AND TALKS DISCOVERY")
    print("="*80)

    # Fetch all works
    print("\n1. Fetching all Haverford works (2020+)...")
    all_works = fetch_haverford_works(from_year=2020)

    print(f"\nTotal works found: {len(all_works)}")

    # Categorize by type
    print("\n2. Categorizing works by type...")
    categories = categorize_works(all_works)

    print(f"\nWork Types Found:")
    for work_type, works_list in sorted(categories.items(), key=lambda x: -len(x[1])):
        print(f"  {work_type}: {len(works_list)}")

    # Focus on conference proceedings (talks/presentations)
    print("\n" + "="*80)
    print("CONFERENCE TALKS/PRESENTATIONS")
    print("="*80)

    talk_types = [
        'proceedings-article',
        'posted-content',
        'peer-review'
    ]

    talks = []
    for talk_type in talk_types:
        if talk_type in categories:
            talks.extend(categories[talk_type])

    print(f"\nTotal potential talks/presentations: {len(talks)}")

    if talks:
        print("\nSample talks:")
        for i, talk in enumerate(talks[:10], 1):
            title = talk.get('title', 'Untitled')
            authors = talk.get('authorships', [])
            author_names = [a.get('author', {}).get('display_name', 'Unknown') for a in authors[:3]]
            year = talk.get('publication_year', 'Unknown')
            venue = talk.get('primary_location', {}).get('source', {}).get('display_name', 'Unknown venue')

            print(f"\n{i}. {title}")
            print(f"   Authors: {', '.join(author_names)}")
            print(f"   Year: {year}")
            print(f"   Venue: {venue}")

    # Extract grants/funding
    print("\n" + "="*80)
    print("GRANTS AND FUNDING")
    print("="*80)

    grants = extract_grants_and_awards(all_works)

    print(f"\nTotal works with grants/funding: {len(grants)}")

    if grants:
        print("\nSample grants:")
        for i, grant in enumerate(grants[:20], 1):
            print(f"\n{i}. {grant['work_title']}")
            print(f"   Funder: {grant['funder']}")
            if grant['award_id']:
                print(f"   Award ID: {grant['award_id']}")

    # Save results
    output_file = f"haverford_awards_talks_{time.strftime('%Y%m%d_%H%M%S')}.json"

    output_data = {
        'total_works': len(all_works),
        'categories': {k: len(v) for k, v in categories.items()},
        'potential_talks': len(talks),
        'works_with_grants': len(grants),
        'sample_talks': talks[:50],  # Save first 50 talks
        'all_grants': grants
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print("\n" + "="*80)
    print(f"Results saved to: {output_file}")
    print("="*80)

    print("\n" + "="*80)
    print("NOTES")
    print("="*80)
    print("""
OpenAlex Limitations:
- No dedicated 'awards' endpoint (awards are in grants/funding metadata)
- No dedicated 'talks' endpoint (conference talks are in 'proceedings-article' type)
- 'posted-content' includes preprints and conference materials

What we found:
- Conference proceedings/talks: Check 'proceedings-article' type
- Grants/funding: Check 'grants' field in works metadata
- Presentations: May be in 'posted-content' or 'proceedings-article'

To get more complete data about awards/talks:
- Faculty CVs or department websites
- Haverford's institutional repository
- ORCID profiles for individual faculty
""")

if __name__ == "__main__":
    main()
