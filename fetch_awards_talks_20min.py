"""
Fetch awards and talks for 20 minutes
Stores as 'Award' and 'Talk' content types (NOT 'Publication')
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
log_file = f'awards_talks_20min_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file, encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

# TIME LIMIT: 20 minutes
TIME_LIMIT_SECONDS = 20 * 60  # 20 minutes

# Create PDF cache directory
PDF_CACHE_DIR = Path("./pdf_cache")
PDF_CACHE_DIR.mkdir(exist_ok=True)

# Import PDF extraction
try:
    import pypdf
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

try:
    import fitz  # PyMuPDF
    PYMUPDF_SUPPORT = True
except ImportError:
    PYMUPDF_SUPPORT = False


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
        except:
            pass

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

    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(pdf_url, headers=headers, timeout=15, allow_redirects=True)
        response.raise_for_status()
        if response.content[:4] == b'%PDF':
            with open(cache_path, 'wb') as f:
                f.write(response.content)
            return response.content
    except:
        pass
    return None


def get_full_text(work: dict) -> tuple:
    """Get full text - returns (text, source)"""
    work_id = work.get('id', '').split('/')[-1]

    # Try PDF
    pdf_url = try_openalex_pdf(work)
    if pdf_url:
        try:
            pdf_content = download_pdf(pdf_url, f"{work_id}.pdf")
            if pdf_content:
                text = extract_text_from_pdf(pdf_content)
                if text and len(text) > 500:
                    return (text, 'pdf')
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
    """Fetch publications to extract grants"""
    publications = []
    headers = {'User-Agent': 'FacultyPulse/1.0'}

    try:
        url = "https://api.openalex.org/works"
        params = {
            'filter': f'author.id:{openalex_id},publication_year:{from_year}-',
            'per_page': 200,
            'sort': 'publication_date:desc'
        }
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        publications = response.json().get('results', [])
        time.sleep(0.1)
    except:
        pass

    return publications


def extract_grants(works: list, faculty_name: str, department: str) -> list:
    """Extract grants/fellowships as Awards"""
    awards = []
    for work in works:
        grants = work.get('grants', [])
        if grants:
            for grant in grants:
                funder = grant.get('funder', '')
                funder_name = funder if isinstance(funder, str) else funder.get('display_name', 'Unknown')
                award_id = grant.get('award_id', '')

                is_fellowship = 'fellowship' in funder_name.lower() or 'fellowship' in award_id.lower()
                award_type = 'Fellowship' if is_fellowship else 'Grant'

                awards.append({
                    'faculty_name': faculty_name,
                    'department': department,
                    'award_type': award_type,
                    'funder': funder_name,
                    'award_id': award_id,
                    'related_work': work.get('title', 'Untitled'),
                    'date': work.get('publication_date', f"{work.get('publication_year', 2020)}-01-01"),
                    'work_id': work.get('id', '')
                })
    return awards


def get_conference_talks(openalex_id: str, from_year: int = 2020):
    """Fetch conference talks"""
    headers = {'User-Agent': 'FacultyPulse/1.0'}
    try:
        url = "https://api.openalex.org/works"
        params = {
            'filter': f'author.id:{openalex_id},publication_year:{from_year}-,type:proceedings-article',
            'per_page': 200,
            'sort': 'publication_date:desc'
        }
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json().get('results', [])
    except:
        return []


def format_award(award: dict) -> str:
    """Format award content"""
    return f"""Faculty: {award['faculty_name']}
Department: {award['department']}

Award Type: {award['award_type']}
Funder: {award['funder']}
Award ID: {award['award_id']}

Related Publication: {award['related_work']}

This {award['award_type'].lower()} was awarded to {award['faculty_name']} from {award['department']}.
"""


def format_talk(talk: dict, faculty_name: str, department: str, openalex_id: str, text: str, source: str) -> str:
    """Format talk content"""
    title = talk.get('title', 'Untitled')
    authors = [a.get('author', {}).get('display_name', '') for a in talk.get('authorships', [])[:10]]
    authors_str = ', '.join(filter(None, authors)) or 'Unknown'
    venue = talk.get('primary_location', {}).get('source', {}).get('display_name', 'Unknown Conference')

    content = f"""Faculty: {faculty_name}
Department: {department}
OpenAlex ID: {openalex_id}

Presentation Title: {title}
Presenters: {authors_str}
Year: {talk.get('publication_year', '')}
Conference/Event: {venue}
Date: {talk.get('publication_date', '')}
Text Source: {source}

"""
    if source == 'pdf':
        content += "Conference Paper:\n" + text + "\n\n"
    elif source == 'abstract':
        content += "Abstract:\n" + text + "\n\n"

    content += f"\nThis presentation was given by {faculty_name} from {department}."
    return content


def process_faculty(faculty_info: dict, chroma: ChromaDBManager, start_time: float) -> dict:
    """Process one faculty - awards and talks only"""
    faculty_name = faculty_info['name']
    department = faculty_info['department']
    openalex_id = faculty_info['openalex_id']

    result = {
        'name': faculty_name,
        'awards_added': 0,
        'talks_added': 0
    }

    # Check time limit
    if time.time() - start_time > TIME_LIMIT_SECONDS:
        return result

    try:
        logger.info(f"Processing: {faculty_name}")

        # Get awards from grants
        publications = fetch_publications_for_grants(openalex_id, from_year=2020)
        awards = extract_grants(publications, faculty_name, department)

        for award in awards:
            if time.time() - start_time > TIME_LIMIT_SECONDS:
                break
            try:
                content = format_award(award)
                work_id = award['work_id'].split('/')[-1] if award['work_id'] else ''

                chroma.add_single_submission(
                    document=content,
                    faculty_name=faculty_name,
                    date_published=award['date'],
                    content_type='Award',  # IMPORTANT: Content type is 'Award'
                    department=department,
                    submission_id=f"award_{openalex_id}_{work_id}" if work_id else None
                )
                result['awards_added'] += 1
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"Award error: {e}")

        # Get conference talks
        talks = get_conference_talks(openalex_id, from_year=2020)
        for talk in talks:
            if time.time() - start_time > TIME_LIMIT_SECONDS:
                break
            try:
                text, source = get_full_text(talk)
                if not text:
                    continue

                content = format_talk(talk, faculty_name, department, openalex_id, text, source)
                work_id = talk.get('id', '').split('/')[-1]

                chroma.add_single_submission(
                    document=content,
                    faculty_name=faculty_name,
                    date_published=talk.get('publication_date', f"{talk.get('publication_year', 2020)}-01-01"),
                    content_type='Talk',  # IMPORTANT: Content type is 'Talk'
                    department=department,
                    submission_id=f"talk_{openalex_id}_{work_id}" if work_id else None
                )
                result['talks_added'] += 1
                time.sleep(0.2)
            except Exception as e:
                logger.error(f"Talk error: {e}")

        logger.info(f"  ✓ Awards: {result['awards_added']}, Talks: {result['talks_added']}")

    except Exception as e:
        logger.error(f"Error: {e}")

    return result


def main():
    print("\n" + "="*80)
    print("FETCH AWARDS + TALKS (20 MINUTE TIME LIMIT)")
    print("="*80 + "\n")

    # Load faculty
    with open('haverford_faculty_with_openalex.json', 'r', encoding='utf-8') as f:
        all_faculty = json.load(f)

    faculty_with_ids = [f for f in all_faculty if f.get('openalex_id') and f['openalex_id'] != 'null']

    print(f"✓ Processing {len(faculty_with_ids)} faculty")
    print(f"✓ Time limit: 20 minutes")
    print(f"✓ Content types: 'Award' and 'Talk' (NOT 'Publication')")
    print()

    start_time = time.time()
    chroma = ChromaDBManager()

    results = []
    for i, faculty in enumerate(faculty_with_ids, 1):
        # Check time limit
        elapsed = time.time() - start_time
        if elapsed > TIME_LIMIT_SECONDS:
            print(f"\n⏱️ Time limit reached ({elapsed/60:.1f} minutes)")
            break

        print(f"[{i}/{len(faculty_with_ids)}] {faculty['name']}")
        result = process_faculty(faculty, chroma, start_time)
        results.append(result)

    # Summary
    elapsed = time.time() - start_time
    total_awards = sum(r['awards_added'] for r in results)
    total_talks = sum(r['talks_added'] for r in results)

    print("\n" + "="*80)
    print("COMPLETE")
    print("="*80)
    print(f"\nTime: {elapsed/60:.1f} minutes")
    print(f"Faculty processed: {len(results)}")
    print(f"\n🏆 Awards added: {total_awards}")
    print(f"🎤 Talks added: {total_talks}")
    print(f"📊 Total: {total_awards + total_talks}")

    # Save results
    results_file = f"awards_talks_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump({
            'elapsed_minutes': elapsed/60,
            'faculty_processed': len(results),
            'total_awards': total_awards,
            'total_talks': total_talks,
            'results': results
        }, f, indent=2)

    print(f"\nSaved: {results_file}")


if __name__ == "__main__":
    main()
