"""
Fetch ONLY awards/grants/fellowships and conference talks from OpenAlex
Skips publications - only gets awards and talks (post-2020)
"""
import sys
import json
import requests
import time
import logging
from pathlib import Path
from datetime import datetime
from chroma_manager import ChromaDBManager

# Fix encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Setup logging
log_file = f'awards_talks_fetch_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file, encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

# Create PDF cache directory
PDF_CACHE_DIR = Path("./pdf_cache")
PDF_CACHE_DIR.mkdir(exist_ok=True)

# Import PDF extraction
try:
    import pypdf
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    logger.warning("pypdf not available")

try:
    import fitz  # PyMuPDF
    PYMUPDF_SUPPORT = True
except ImportError:
    PYMUPDF_SUPPORT = False
    logger.warning("PyMuPDF not available")


def extract_text_from_pdf(pdf_content: bytes) -> str:
    """Extract text from PDF content"""
    if PYMUPDF_SUPPORT:
        try:
            pdf_document = fitz.open(stream=pdf_content, filetype="pdf")
            text = ""
            for page_num in range(pdf_document.page_count):
                page = pdf_document[page_num]
                text += page.get_text()
            pdf_document.close()
            text = ' '.join(text.split())
            return text
        except Exception as e:
            logger.debug(f"PyMuPDF failed: {e}")

    if PDF_SUPPORT:
        try:
            import io
            pdf_file = io.BytesIO(pdf_content)
            pdf_reader = pypdf.PdfReader(pdf_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            text = ' '.join(text.split())
            return text
        except Exception as e:
            logger.debug(f"pypdf failed: {e}")

    return None


def try_unpaywall_pdf(doi: str) -> str:
    """Try to get PDF URL from Unpaywall"""
    if not doi:
        return None
    try:
        clean_doi = doi.replace('https://doi.org/', '')
        url = f"https://api.unpaywall.org/v2/{clean_doi}?email=research@example.com"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('is_oa'):
                best_oa = data.get('best_oa_location', {})
                pdf_url = best_oa.get('url_for_pdf')
                if pdf_url:
                    return pdf_url
    except:
        pass
    return None


def try_openalex_pdf(work: dict) -> str:
    """Try to get PDF URL from OpenAlex work data"""
    try:
        locations = work.get('locations', [])
        for location in locations:
            if location.get('is_oa'):
                pdf_url = location.get('pdf_url')
                if pdf_url:
                    return pdf_url
        best_oa = work.get('best_oa_location', {})
        if best_oa:
            pdf_url = best_oa.get('pdf_url')
            if pdf_url:
                return pdf_url
    except:
        pass
    return None


def download_pdf(pdf_url: str, cache_filename: str) -> bytes:
    """Download PDF from URL"""
    cache_path = PDF_CACHE_DIR / cache_filename

    if cache_path.exists():
        with open(cache_path, 'rb') as f:
            return f.read()

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    try:
        response = requests.get(pdf_url, headers=headers, timeout=30, allow_redirects=True)
        response.raise_for_status()

        if not response.content[:4] == b'%PDF':
            return None

        with open(cache_path, 'wb') as f:
            f.write(response.content)

        return response.content
    except:
        return None


def get_full_text_from_publication(work: dict) -> tuple:
    """
    Try to get full text from a publication
    Returns: (full_text, source) where source is 'pdf', 'abstract', or 'none'
    """
    doi = work.get('doi', '')
    work_id = work.get('id', '').split('/')[-1]

    # Try to find PDF URL
    pdf_url = try_openalex_pdf(work)
    if not pdf_url and doi:
        pdf_url = try_unpaywall_pdf(doi)

    # If we found a PDF URL, download and extract
    if pdf_url:
        try:
            cache_filename = f"{work_id}.pdf"
            pdf_content = download_pdf(pdf_url, cache_filename)
            if pdf_content:
                full_text = extract_text_from_pdf(pdf_content)
                if full_text and len(full_text) > 500:
                    return (full_text, 'pdf')
        except:
            pass

    # Fall back to abstract
    abstract = work.get('abstract', '')
    if not abstract:
        abstract_idx = work.get('abstract_inverted_index', {})
        if isinstance(abstract_idx, dict) and abstract_idx:
            try:
                max_pos = max(max(positions) for positions in abstract_idx.values())
                words = [''] * (max_pos + 1)
                for word, positions in abstract_idx.items():
                    for pos in positions:
                        words[pos] = word
                abstract = ' '.join(words)
            except:
                pass

    if abstract:
        return (abstract, 'abstract')

    return (None, 'none')


def fetch_publications_for_grants(openalex_id: str, from_year: int = 2020):
    """Fetch publications to extract grants from them"""
    publications = []
    page = 1
    per_page = 50
    headers = {'User-Agent': 'FacultyPulse/1.0 (mailto:research@example.com)'}

    while True:
        try:
            url = "https://api.openalex.org/works"
            params = {
                'filter': f'author.id:{openalex_id},publication_year:{from_year}-',
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

            publications.extend(results)

            meta = data.get('meta', {})
            if page * per_page >= meta.get('count', 0):
                break

            page += 1
            time.sleep(0.1)
        except Exception as e:
            logger.error(f"Error fetching publications for grants: {e}")
            break

    return publications


def extract_grants_from_works(works: list, faculty_name: str, department: str) -> list:
    """Extract grants/fellowships from works (count as Awards)"""
    awards = []

    for work in works:
        grants = work.get('grants', [])
        if grants:
            for grant in grants:
                funder = grant.get('funder', '')
                funder_name = funder if isinstance(funder, str) else funder.get('display_name', 'Unknown Funder')
                award_id = grant.get('award_id', '')

                # Check if it's a fellowship
                is_fellowship = 'fellowship' in funder_name.lower() or 'fellowship' in award_id.lower()
                award_type = 'Fellowship' if is_fellowship else 'Grant'

                work_title = work.get('title', 'Untitled')
                work_year = work.get('publication_year', '')
                work_date = work.get('publication_date', f"{work_year}-01-01")

                awards.append({
                    'faculty_name': faculty_name,
                    'department': department,
                    'award_type': award_type,
                    'funder': funder_name,
                    'award_id': award_id,
                    'related_work': work_title,
                    'date': work_date,
                    'work_id': work.get('id', '')
                })

    return awards


def get_conference_talks(openalex_id: str, from_year: int = 2020):
    """Fetch conference proceedings/talks"""
    talks = []
    headers = {'User-Agent': 'FacultyPulse/1.0 (mailto:research@example.com)'}

    # Fetch proceedings-articles (conference talks)
    try:
        url = "https://api.openalex.org/works"
        params = {
            'filter': f'author.id:{openalex_id},publication_year:{from_year}-,type:proceedings-article',
            'per_page': 200,
            'sort': 'publication_date:desc'
        }

        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()

        data = response.json()
        talks = data.get('results', [])

    except Exception as e:
        logger.error(f"Error fetching conference talks: {e}")

    return talks


def format_award_content(award: dict) -> str:
    """Format award/grant content"""
    content = f"""Faculty: {award['faculty_name']}
Department: {award['department']}

Award Type: {award['award_type']}
Funder: {award['funder']}
Award ID: {award['award_id']}

Related Publication: {award['related_work']}

This {award['award_type'].lower()} was awarded to {award['faculty_name']} from {award['department']}.
"""
    return content


def format_talk_content(talk: dict, faculty_name: str, department: str, openalex_id: str, full_text: str, source: str) -> str:
    """Format conference talk/presentation content"""
    title = talk.get('title', 'Untitled')
    talk_year = talk.get('publication_year', '')
    talk_date = talk.get('publication_date', '')

    authors = []
    for authorship in talk.get('authorships', [])[:10]:
        author_info = authorship.get('author', {})
        if author_info.get('display_name'):
            authors.append(author_info['display_name'])
    authors_str = ', '.join(authors) if authors else 'Unknown'

    venue = talk.get('primary_location', {}).get('source', {})
    venue_name = venue.get('display_name', 'Unknown Conference')
    doi = talk.get('doi', '')

    content = f"""Faculty: {faculty_name}
Department: {department}
OpenAlex ID: {openalex_id}

Presentation Title: {title}
Presenters: {authors_str}
Year: {talk_year}
Conference/Event: {venue_name}
"""

    if doi:
        content += f"DOI: {doi}\n"
    if talk_date:
        content += f"Date: {talk_date}\n"

    content += f"\nText Source: {source}\n\n"

    if source == 'pdf':
        content += "Conference Paper:\n"
        content += full_text + "\n\n"
    elif source == 'abstract':
        content += "Abstract:\n"
        content += full_text + "\n\n"

    content += f"\nThis presentation was given by {faculty_name} from {department}."
    return content


def process_faculty(faculty_info: dict, chroma: ChromaDBManager) -> dict:
    """Process one faculty member - ONLY awards and talks"""
    faculty_name = faculty_info['name']
    department = faculty_info['department']
    openalex_id = faculty_info['openalex_id']

    result = {
        'name': faculty_name,
        'department': department,
        'openalex_id': openalex_id,
        'awards_found': 0,
        'awards_added': 0,
        'talks_found': 0,
        'talks_added': 0,
        'talks_pdf_count': 0,
        'talks_abstract_count': 0,
        'talks_failed': 0
    }

    try:
        logger.info(f"\n{'='*80}")
        logger.info(f"Processing: {faculty_name} ({department})")
        logger.info(f"OpenAlex ID: {openalex_id}")

        # 1. FETCH GRANTS/AWARDS FROM PUBLICATIONS
        publications = fetch_publications_for_grants(openalex_id, from_year=2020)
        awards = extract_grants_from_works(publications, faculty_name, department)
        result['awards_found'] = len(awards)

        if awards:
            logger.info(f"  Found {len(awards)} grants/fellowships")

            for award in awards:
                try:
                    content = format_award_content(award)
                    work_id = award['work_id'].split('/')[-1] if award['work_id'] else ''
                    submission_id = f"award_{openalex_id}_{work_id}" if work_id else None

                    chroma.add_single_submission(
                        document=content,
                        faculty_name=faculty_name,
                        date_published=award['date'],
                        content_type='Award',
                        department=department,
                        submission_id=submission_id
                    )

                    result['awards_added'] += 1
                    time.sleep(0.2)

                except Exception as e:
                    logger.error(f"  Error processing award: {e}")

        # 2. FETCH CONFERENCE TALKS
        talks = get_conference_talks(openalex_id, from_year=2020)
        result['talks_found'] = len(talks)

        if talks:
            logger.info(f"  Found {len(talks)} conference talks")

            for talk in talks:
                try:
                    full_text, source = get_full_text_from_publication(talk)

                    if not full_text:
                        result['talks_failed'] += 1
                        continue

                    if source == 'pdf':
                        result['talks_pdf_count'] += 1
                    elif source == 'abstract':
                        result['talks_abstract_count'] += 1

                    content = format_talk_content(talk, faculty_name, department, openalex_id, full_text, source)
                    talk_date = talk.get('publication_date', '') or f"{talk.get('publication_year', 2020)}-01-01"
                    work_id = talk.get('id', '').split('/')[-1]
                    submission_id = f"talk_{openalex_id}_{work_id}" if work_id else None

                    chroma.add_single_submission(
                        document=content,
                        faculty_name=faculty_name,
                        date_published=talk_date,
                        content_type='Talk',
                        department=department,
                        submission_id=submission_id
                    )

                    result['talks_added'] += 1
                    time.sleep(0.3)

                except Exception as e:
                    result['talks_failed'] += 1
                    logger.error(f"  Error processing talk: {e}")

        logger.info(f"  ✓ Completed:")
        logger.info(f"    Awards: {result['awards_added']}")
        logger.info(f"    Talks: {result['talks_added']} ({result['talks_pdf_count']} PDF, {result['talks_abstract_count']} abstract)")

    except Exception as e:
        logger.error(f"  ✗ Error processing faculty: {e}")

    return result


def main():
    """Main execution"""
    print("\n" + "="*80)
    print("BULK FACULTY FETCHER: AWARDS + TALKS ONLY")
    print("="*80 + "\n")

    # Load faculty data
    print("Loading faculty data from haverford_faculty_with_openalex.json...")
    try:
        with open('haverford_faculty_with_openalex.json', 'r', encoding='utf-8') as f:
            all_faculty = json.load(f)
    except Exception as e:
        print(f"✗ Error loading faculty data: {e}")
        return

    # Filter for faculty with OpenAlex IDs
    faculty_with_ids = [
        f for f in all_faculty
        if f.get('openalex_id') and f['openalex_id'] != 'null'
    ]

    print(f"✓ Found {len(faculty_with_ids)} faculty with OpenAlex IDs")
    print(f"✓ Total faculty in file: {len(all_faculty)}")
    print()

    # Department breakdown
    from collections import Counter
    dept_counts = Counter(f['department'] for f in faculty_with_ids)
    print("Faculty by department:")
    for dept, count in sorted(dept_counts.items(), key=lambda x: -x[1]):
        print(f"  {dept}: {count}")
    print()

    # Confirmation
    print(f"About to process {len(faculty_with_ids)} faculty members.")
    print("This will fetch ONLY:")
    print("  - Grants and Fellowships (counted as Awards)")
    print("  - Conference Talks/Presentations")
    print("  - Skipping regular publications")
    print(f"Estimated time: 1-2 hours")
    print(f"Log file: {log_file}")
    print()

    start_time = time.time()

    # Initialize database
    chroma = ChromaDBManager()

    # Process all faculty
    results = []
    for i, faculty in enumerate(faculty_with_ids, 1):
        print(f"\n[{i}/{len(faculty_with_ids)}] {faculty['name']} ({faculty['department']})")

        result = process_faculty(faculty, chroma)
        results.append(result)

        # Progress update every 10 faculty
        if i % 10 == 0:
            elapsed = time.time() - start_time
            avg_time = elapsed / i
            remaining = (len(faculty_with_ids) - i) * avg_time
            print(f"\nProgress: {i}/{len(faculty_with_ids)} ({i/len(faculty_with_ids)*100:.1f}%)")
            print(f"Elapsed: {elapsed/60:.1f} min, Estimated remaining: {remaining/60:.1f} min")

    # Final summary
    elapsed = time.time() - start_time

    print("\n" + "="*80)
    print("BULK PROCESSING COMPLETE")
    print("="*80)

    total_awards_found = sum(r['awards_found'] for r in results)
    total_awards_added = sum(r['awards_added'] for r in results)
    total_talks_found = sum(r['talks_found'] for r in results)
    total_talks_added = sum(r['talks_added'] for r in results)
    total_talks_pdf = sum(r['talks_pdf_count'] for r in results)
    total_talks_abstract = sum(r['talks_abstract_count'] for r in results)

    print(f"\nTime elapsed: {elapsed/60:.1f} minutes ({elapsed/3600:.1f} hours)")
    print(f"\nFaculty processed: {len(results)}")

    print(f"\n🏆 AWARDS/GRANTS/FELLOWSHIPS:")
    print(f"  Found: {total_awards_found}")
    print(f"  Added: {total_awards_added}")

    print(f"\n🎤 CONFERENCE TALKS:")
    print(f"  Found: {total_talks_found}")
    print(f"  Added: {total_talks_added}")
    print(f"    - With full PDF text: {total_talks_pdf} ({total_talks_pdf/total_talks_added*100 if total_talks_added > 0 else 0:.1f}%)")
    print(f"    - With abstract only: {total_talks_abstract} ({total_talks_abstract/total_talks_added*100 if total_talks_added > 0 else 0:.1f}%)")

    print(f"\n📊 TOTAL DOCUMENTS ADDED: {total_awards_added + total_talks_added}")

    # Save results
    results_file = f"awards_talks_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {results_file}")
    print(f"Log file: {log_file}")

    print("\n" + "="*80)


if __name__ == "__main__":
    main()
