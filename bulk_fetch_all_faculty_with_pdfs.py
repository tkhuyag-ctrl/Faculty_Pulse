"""
Bulk fetch ALL faculty publications from OpenAlex with FULL PDF TEXT extraction
Processes all faculty with OpenAlex IDs from haverford_faculty_with_openalex.json
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
log_file = f'bulk_faculty_fetch_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
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
    # Try PyMuPDF first
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

    # Fall back to pypdf
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


def fetch_publications(openalex_id: str, from_year: int = 2020):
    """Fetch publications from OpenAlex"""
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
            logger.error(f"Error fetching page {page}: {e}")
            break

    return publications


def format_publication_content(pub: dict, faculty_name: str, department: str, openalex_id: str, full_text: str, source: str) -> str:
    """Format publication with full text"""
    title = pub.get('title', 'Untitled')
    pub_year = pub.get('publication_year', '')
    pub_date = pub.get('publication_date', '')

    authors = []
    for authorship in pub.get('authorships', [])[:10]:
        author_info = authorship.get('author', {})
        if author_info.get('display_name'):
            authors.append(author_info['display_name'])
    authors_str = ', '.join(authors) if authors else 'Unknown'

    venue = pub.get('primary_location', {}).get('source', {})
    venue_name = venue.get('display_name', 'Unknown venue')
    doi = pub.get('doi', '')
    cited_by_count = pub.get('cited_by_count', 0)
    pub_type = pub.get('type', 'article')

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

    content += f"Text Source: {source}\n\n"

    if source == 'pdf':
        content += "================================================================================\n"
        content += "FULL PAPER TEXT:\n"
        content += "================================================================================\n\n"
        content += full_text + "\n\n"
    elif source == 'abstract':
        content += "Abstract:\n"
        content += full_text + "\n\n"

    content += f"\nThis publication is by {faculty_name} from {department}."
    return content


def process_faculty(faculty_info: dict, chroma: ChromaDBManager) -> dict:
    """Process one faculty member"""
    faculty_name = faculty_info['name']
    department = faculty_info['department']
    openalex_id = faculty_info['openalex_id']

    result = {
        'name': faculty_name,
        'department': department,
        'openalex_id': openalex_id,
        'publications_found': 0,
        'added': 0,
        'pdf_count': 0,
        'abstract_count': 0,
        'failed': 0
    }

    try:
        logger.info(f"\n{'='*80}")
        logger.info(f"Processing: {faculty_name} ({department})")
        logger.info(f"OpenAlex ID: {openalex_id}")

        # Fetch publications
        publications = fetch_publications(openalex_id, from_year=2020)
        result['publications_found'] = len(publications)

        if not publications:
            logger.info(f"  No publications found since 2020")
            return result

        logger.info(f"  Found {len(publications)} publications")

        # Process each publication
        for i, pub in enumerate(publications, 1):
            try:
                title = pub.get('title', 'Untitled')

                # Get full text
                full_text, source = get_full_text_from_publication(pub)

                if not full_text:
                    result['failed'] += 1
                    continue

                if source == 'pdf':
                    result['pdf_count'] += 1
                elif source == 'abstract':
                    result['abstract_count'] += 1

                # Format content
                content = format_publication_content(pub, faculty_name, department, openalex_id, full_text, source)

                # Get publication date
                pub_date = pub.get('publication_date', '') or f"{pub.get('publication_year', 2020)}-01-01"

                # Get work ID for unique submission ID
                work_id = pub.get('id', '').split('/')[-1]
                submission_id = f"pub_{openalex_id}_{work_id}" if work_id else None

                # Add to database
                chroma.add_single_submission(
                    document=content,
                    faculty_name=faculty_name,
                    date_published=pub_date,
                    content_type='Publication',
                    department=department,
                    submission_id=submission_id
                )

                result['added'] += 1

                # Small delay
                time.sleep(0.3)

            except Exception as e:
                result['failed'] += 1
                logger.error(f"  Error processing publication: {e}")

        logger.info(f"  ✓ Completed: {result['added']} added ({result['pdf_count']} PDF, {result['abstract_count']} abstract), {result['failed']} failed")

    except Exception as e:
        logger.error(f"  ✗ Error processing faculty: {e}")

    return result


def main():
    """Main execution"""
    print("\n" + "="*80)
    print("BULK FACULTY PUBLICATION FETCHER WITH FULL PDF TEXT")
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
    print("This will fetch publications from 2020+ and attempt to download PDFs.")
    print(f"Estimated time: 2-4 hours")
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

    total_found = sum(r['publications_found'] for r in results)
    total_added = sum(r['added'] for r in results)
    total_pdf = sum(r['pdf_count'] for r in results)
    total_abstract = sum(r['abstract_count'] for r in results)
    total_failed = sum(r['failed'] for r in results)

    print(f"\nTime elapsed: {elapsed/60:.1f} minutes ({elapsed/3600:.1f} hours)")
    print(f"\nFaculty processed: {len(results)}")
    print(f"Publications found: {total_found}")
    print(f"Publications added: {total_added}")
    print(f"  - With full PDF text: {total_pdf} ({total_pdf/total_added*100 if total_added > 0 else 0:.1f}%)")
    print(f"  - With abstract only: {total_abstract} ({total_abstract/total_added*100 if total_added > 0 else 0:.1f}%)")
    print(f"Failed/Skipped: {total_failed}")

    # Top departments by PDF success
    dept_stats = {}
    for r in results:
        dept = r['department']
        if dept not in dept_stats:
            dept_stats[dept] = {'pdf': 0, 'abstract': 0, 'total': 0}
        dept_stats[dept]['pdf'] += r['pdf_count']
        dept_stats[dept]['abstract'] += r['abstract_count']
        dept_stats[dept]['total'] += r['added']

    print("\nPDF Success Rate by Department:")
    for dept in sorted(dept_stats.keys(), key=lambda d: dept_stats[d]['pdf']/(dept_stats[d]['total'] or 1), reverse=True):
        stats = dept_stats[dept]
        if stats['total'] > 0:
            pdf_rate = stats['pdf'] / stats['total'] * 100
            print(f"  {dept}: {stats['pdf']}/{stats['total']} ({pdf_rate:.1f}%)")

    # Save results
    results_file = f"bulk_fetch_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {results_file}")
    print(f"Log file: {log_file}")

    print("\n" + "="*80)
    print("NEXT STEPS:")
    print("="*80)
    print("1. Verify database: python inspect_database.py")
    print("2. Test retrieval: python -c \"from chroma_manager import ChromaDBManager; m = ChromaDBManager(); print(f'Total docs: {m.collection.count()}')\"")
    print("3. Test chatbot: streamlit run app.py")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
