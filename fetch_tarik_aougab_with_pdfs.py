"""
Fetch Tarik Aougab's publications from OpenAlex with FULL PDF TEXT extraction
Test script to verify the full pipeline works before bulk processing
"""
import sys
import requests
import time
import logging
import os
from pathlib import Path
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
        logging.FileHandler(f'tarik_aougab_pdfs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log', encoding='utf-8')
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
    logger.info("pypdf library available")
except ImportError:
    PDF_SUPPORT = False
    logger.warning("pypdf not available")

try:
    import fitz  # PyMuPDF
    PYMUPDF_SUPPORT = True
    logger.info("PyMuPDF library available")
except ImportError:
    PYMUPDF_SUPPORT = False
    logger.warning("PyMuPDF not available")


def extract_text_from_pdf(pdf_content: bytes) -> str:
    """Extract text from PDF content"""
    logger.info(f"Extracting text from PDF (size: {len(pdf_content)} bytes)")

    # Try PyMuPDF first
    if PYMUPDF_SUPPORT:
        try:
            pdf_document = fitz.open(stream=pdf_content, filetype="pdf")
            page_count = pdf_document.page_count
            logger.info(f"PDF has {page_count} pages")

            text = ""
            for page_num in range(page_count):
                page = pdf_document[page_num]
                text += page.get_text()
            pdf_document.close()

            # Clean up text
            text = ' '.join(text.split())
            logger.info(f"✓ Extracted {len(text)} characters using PyMuPDF")
            return text
        except Exception as e:
            logger.warning(f"PyMuPDF failed: {e}, trying pypdf...")

    # Fall back to pypdf
    if PDF_SUPPORT:
        try:
            import io
            pdf_file = io.BytesIO(pdf_content)
            pdf_reader = pypdf.PdfReader(pdf_file)
            page_count = len(pdf_reader.pages)
            logger.info(f"PDF has {page_count} pages")

            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()

            text = ' '.join(text.split())
            logger.info(f"✓ Extracted {len(text)} characters using pypdf")
            return text
        except Exception as e:
            logger.error(f"pypdf failed: {e}")
            raise

    raise Exception("No PDF extraction library available")


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
                    logger.info(f"  Found PDF via Unpaywall: {pdf_url}")
                    return pdf_url
        return None
    except Exception as e:
        logger.debug(f"  Unpaywall lookup failed: {e}")
        return None


def try_openalex_pdf(work: dict) -> str:
    """Try to get PDF URL from OpenAlex work data"""
    try:
        # Check locations for PDF URLs
        locations = work.get('locations', [])
        for location in locations:
            if location.get('is_oa'):
                pdf_url = location.get('pdf_url')
                if pdf_url:
                    logger.info(f"  Found PDF via OpenAlex: {pdf_url}")
                    return pdf_url

        # Check best_oa_location
        best_oa = work.get('best_oa_location', {})
        if best_oa:
            pdf_url = best_oa.get('pdf_url')
            if pdf_url:
                logger.info(f"  Found PDF via OpenAlex best OA: {pdf_url}")
                return pdf_url

        return None
    except Exception as e:
        logger.debug(f"  OpenAlex PDF lookup failed: {e}")
        return None


def download_pdf(pdf_url: str, cache_filename: str) -> bytes:
    """Download PDF from URL"""
    cache_path = PDF_CACHE_DIR / cache_filename

    # Check cache first
    if cache_path.exists():
        logger.info(f"  Using cached PDF: {cache_filename}")
        with open(cache_path, 'rb') as f:
            return f.read()

    # Download PDF
    logger.info(f"  Downloading PDF from: {pdf_url}")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        response = requests.get(pdf_url, headers=headers, timeout=30, allow_redirects=True)
        response.raise_for_status()

        # Verify it's actually a PDF
        if not response.content[:4] == b'%PDF':
            logger.warning(f"  Downloaded content is not a PDF")
            return None

        # Cache it
        with open(cache_path, 'wb') as f:
            f.write(response.content)

        logger.info(f"  ✓ Downloaded and cached PDF ({len(response.content)} bytes)")
        return response.content

    except Exception as e:
        logger.error(f"  Failed to download PDF: {e}")
        return None


def get_full_text_from_publication(work: dict) -> tuple:
    """
    Try to get full text from a publication
    Returns: (full_text, source) where source is 'pdf', 'abstract', or 'none'
    """
    title = work.get('title', 'Untitled')
    doi = work.get('doi', '')
    work_id = work.get('id', '').split('/')[-1]

    logger.info(f"Attempting to get full text for: {title[:50]}...")

    # Try to find PDF URL
    pdf_url = None

    # Try OpenAlex first
    pdf_url = try_openalex_pdf(work)

    # Try Unpaywall if no luck
    if not pdf_url and doi:
        pdf_url = try_unpaywall_pdf(doi)

    # If we found a PDF URL, download and extract
    if pdf_url:
        try:
            cache_filename = f"{work_id}.pdf"
            pdf_content = download_pdf(pdf_url, cache_filename)

            if pdf_content:
                full_text = extract_text_from_pdf(pdf_content)
                if len(full_text) > 500:  # Reasonable length check
                    logger.info(f"  ✓ Got full PDF text ({len(full_text)} chars)")
                    return (full_text, 'pdf')
                else:
                    logger.warning(f"  PDF text too short ({len(full_text)} chars), using abstract")
        except Exception as e:
            logger.error(f"  Failed to extract PDF text: {e}")

    # Fall back to abstract
    logger.info(f"  No PDF available, using abstract only")
    abstract = work.get('abstract', '')
    if not abstract:
        abstract_idx = work.get('abstract_inverted_index', {})
        if isinstance(abstract_idx, dict) and abstract_idx:
            max_pos = max(max(positions) for positions in abstract_idx.values())
            words = [''] * (max_pos + 1)
            for word, positions in abstract_idx.items():
                for pos in positions:
                    words[pos] = word
            abstract = ' '.join(words)

    if abstract:
        return (abstract, 'abstract')

    return (None, 'none')


def fetch_publications(openalex_id: str, from_year: int = 2020):
    """Fetch publications from OpenAlex"""
    logger.info(f"Fetching publications for {openalex_id} (from {from_year})")

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

            logger.info(f"Fetching page {page}...")
            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()
            results = data.get('results', [])

            if not results:
                break

            publications.extend(results)
            logger.info(f"  Fetched {len(results)} publications")

            meta = data.get('meta', {})
            if page * per_page >= meta.get('count', 0):
                break

            page += 1
            time.sleep(0.1)

        except Exception as e:
            logger.error(f"Error fetching: {e}", exc_info=True)
            break

    logger.info(f"Total publications fetched: {len(publications)}")
    return publications


def format_publication_content(pub: dict, faculty_name: str, department: str, openalex_id: str, full_text: str, source: str) -> str:
    """Format publication with full text"""

    title = pub.get('title', 'Untitled')
    pub_year = pub.get('publication_year', '')
    pub_date = pub.get('publication_date', '')

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

    # Build content - IMPORTANT: Include faculty name throughout!
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

    # Add faculty name again at the end
    content += f"\nThis publication is by {faculty_name} from {department}."

    return content


def add_to_database(publications, faculty_name: str, department: str, openalex_id: str):
    """Add publications with full text to ChromaDB"""
    logger.info(f"Adding {len(publications)} publications to database")

    chroma = ChromaDBManager()

    added = 0
    failed = 0
    pdf_count = 0
    abstract_count = 0

    for i, pub in enumerate(publications, 1):
        try:
            title = pub.get('title', 'Untitled')
            logger.info(f"\n[{i}/{len(publications)}] Processing: {title[:60]}...")

            # Get full text
            full_text, source = get_full_text_from_publication(pub)

            if not full_text:
                logger.warning(f"  No text available, skipping")
                failed += 1
                continue

            if source == 'pdf':
                pdf_count += 1
            else:
                abstract_count += 1

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

            added += 1
            logger.info(f"  ✓ Added successfully (source: {source})")

            # Small delay between publications
            time.sleep(0.5)

        except Exception as e:
            failed += 1
            logger.error(f"  ✗ Failed to add: {str(e)}")

    logger.info(f"\nSummary: {added} added ({pdf_count} with PDF, {abstract_count} with abstract only), {failed} failed")
    return added, failed, pdf_count, abstract_count


def main():
    """Main execution"""
    print("\n" + "="*80)
    print("TARIK AOUGAB PUBLICATION FETCHER WITH FULL PDF TEXT")
    print("="*80 + "\n")

    # Tarik Aougab's information from haverford_faculty_with_openalex.json
    faculty_name = "Tarik Aougab"
    department = "Mathematics"
    openalex_id = "A5065687388"

    print(f"Faculty: {faculty_name}")
    print(f"Department: {department}")
    print(f"OpenAlex ID: {openalex_id}")
    print(f"Expected works: 44 (from OpenAlex profile)")
    print()

    # Fetch publications
    print("Step 1: Fetching publications from OpenAlex (2020+)...")
    publications = fetch_publications(openalex_id, from_year=2020)

    if not publications:
        print("✗ No publications found")
        return

    print(f"✓ Found {len(publications)} publications\n")

    # Download PDFs and add to database
    print("Step 2: Downloading PDFs and extracting full text...")
    print("(This may take a while...)\n")

    added, failed, pdf_count, abstract_count = add_to_database(
        publications, faculty_name, department, openalex_id
    )

    print(f"\n✓ Complete!")
    print(f"  Successfully added: {added}")
    print(f"    - With full PDF text: {pdf_count}")
    print(f"    - With abstract only: {abstract_count}")
    if failed > 0:
        print(f"  Failed/Skipped: {failed}")

    print("\n" + "="*80)
    print("NEXT STEPS:")
    print("="*80)
    print("1. Verify database: python inspect_database.py")
    print("2. Test retrieval with: python -c \"from chroma_manager import ChromaDBManager; m = ChromaDBManager(); r = m.query_submissions('Tarik Aougab', n_results=5); print(f'Found {len(r[\\\"ids\\\"][0])} results')\"")
    print("3. Test chatbot: streamlit run app.py")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
