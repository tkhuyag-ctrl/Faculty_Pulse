"""
Download and Extract Full PDF Content for Faculty Publications
- Tries multiple sources for PDFs (Unpaywall, arXiv, OpenAlex, DOI resolution)
- Extracts full text from PDFs
- Updates ChromaDB with actual paper content
"""
import json
import requests
import time
import logging
import os
import re
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import tempfile
from urllib.parse import urlparse
import pypdf
from chroma_manager import ChromaDBManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('pdf_extraction.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

# Create temp directory for PDFs
PDF_CACHE_DIR = Path("./pdf_cache")
PDF_CACHE_DIR.mkdir(exist_ok=True)


def clean_text(text: str) -> str:
    """Clean extracted text from PDFs"""
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove page numbers and headers/footers (common patterns)
    text = re.sub(r'\n\d+\n', '\n', text)
    return text.strip()


def try_unpaywall_pdf(doi: str) -> Optional[str]:
    """Try to get PDF URL from Unpaywall API"""
    if not doi:
        return None

    try:
        clean_doi = doi.replace('https://doi.org/', '')
        email = "research@example.com"
        url = f"https://api.unpaywall.org/v2/{clean_doi}?email={email}"

        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('is_oa'):
                best_oa = data.get('best_oa_location', {})
                pdf_url = best_oa.get('url_for_pdf')
                if pdf_url:
                    logger.info(f"  Unpaywall: Found PDF URL")
                    return pdf_url

        return None

    except Exception as e:
        logger.debug(f"  Unpaywall failed: {e}")
        return None


def try_openalex_pdf(openalex_work_id: str) -> Optional[str]:
    """Try to get PDF URL from OpenAlex work details"""
    if not openalex_work_id:
        return None

    try:
        # Ensure full URL
        if not openalex_work_id.startswith('http'):
            openalex_work_id = f"https://openalex.org/{openalex_work_id}"

        headers = {
            'User-Agent': 'mailto:research@example.com',
            'Accept': 'application/json'
        }

        response = requests.get(openalex_work_id, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()

            # Check for open access locations
            locations = data.get('locations', []) or data.get('open_access', {}).get('oa_locations', [])

            for location in locations:
                if location.get('is_oa'):
                    pdf_url = location.get('pdf_url')
                    if pdf_url:
                        logger.info(f"  OpenAlex: Found PDF URL")
                        return pdf_url

            # Check primary location
            primary = data.get('primary_location', {})
            if primary and primary.get('is_oa'):
                pdf_url = primary.get('pdf_url')
                if pdf_url:
                    logger.info(f"  OpenAlex primary: Found PDF URL")
                    return pdf_url

        return None

    except Exception as e:
        logger.debug(f"  OpenAlex failed: {e}")
        return None


def try_arxiv_pdf(title: str, doi: str = None) -> Optional[str]:
    """Try to find paper on arXiv"""
    try:
        # Check if DOI contains arxiv
        if doi and 'arxiv' in doi.lower():
            arxiv_id = doi.split('/')[-1]
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            logger.info(f"  arXiv: Found via DOI")
            return pdf_url

        # Search arXiv by title
        if title:
            search_url = "http://export.arxiv.org/api/query"
            params = {
                'search_query': f'ti:{title}',
                'max_results': 1
            }

            response = requests.get(search_url, params=params, timeout=10)

            if response.status_code == 200 and 'arxiv.org/abs/' in response.text:
                # Extract arXiv ID from response
                match = re.search(r'arxiv\.org/abs/(\d+\.\d+)', response.text)
                if match:
                    arxiv_id = match.group(1)
                    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
                    logger.info(f"  arXiv: Found via search")
                    return pdf_url

        return None

    except Exception as e:
        logger.debug(f"  arXiv failed: {e}")
        return None


def download_pdf(pdf_url: str, output_path: Path) -> bool:
    """Download PDF from URL"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(pdf_url, headers=headers, timeout=30, stream=True)

        if response.status_code == 200:
            # Check if it's actually a PDF
            content_type = response.headers.get('Content-Type', '')
            if 'pdf' not in content_type.lower() and not pdf_url.endswith('.pdf'):
                logger.warning(f"  URL may not be a PDF: {content_type}")
                # Try anyway, might still be a PDF

            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info(f"  Downloaded PDF: {output_path.name}")
            return True
        else:
            logger.warning(f"  Download failed: HTTP {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"  Download error: {e}")
        return False


def extract_text_from_pdf(pdf_path: Path) -> Optional[str]:
    """Extract text content from PDF file"""
    try:
        with open(pdf_path, 'rb') as f:
            pdf_reader = pypdf.PdfReader(f)

            num_pages = len(pdf_reader.pages)
            logger.info(f"  Extracting text from {num_pages} pages")

            text_parts = []
            for i, page in enumerate(pdf_reader.pages):
                try:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
                except Exception as e:
                    logger.warning(f"  Failed to extract page {i+1}: {e}")
                    continue

            if text_parts:
                full_text = "\n\n".join(text_parts)
                full_text = clean_text(full_text)

                word_count = len(full_text.split())
                logger.info(f"  Extracted {word_count} words")

                return full_text
            else:
                logger.warning(f"  No text extracted from PDF")
                return None

    except Exception as e:
        logger.error(f"  PDF extraction error: {e}")
        return None


def find_and_extract_pdf(publication: Dict, faculty: Dict) -> Tuple[Optional[str], Optional[str]]:
    """
    Try multiple sources to find, download, and extract PDF content

    Args:
        publication: Publication dictionary with DOI, title, etc.
        faculty: Faculty dictionary with OpenAlex ID

    Returns:
        Tuple of (pdf_text, pdf_url) if successful, (None, None) otherwise
    """
    title = publication.get('title', '')
    doi = publication.get('doi', '')
    openalex_work_id = publication.get('id', '')

    logger.info(f"  Searching for PDF: {title[:60]}...")

    # Try multiple sources in order
    pdf_url = None
    sources = [
        ('Unpaywall', lambda: try_unpaywall_pdf(doi)),
        ('OpenAlex', lambda: try_openalex_pdf(openalex_work_id)),
        ('arXiv', lambda: try_arxiv_pdf(title, doi))
    ]

    for source_name, source_func in sources:
        try:
            pdf_url = source_func()
            if pdf_url:
                logger.info(f"  Found PDF via {source_name}")
                break
            time.sleep(0.2)  # Rate limiting between sources
        except Exception as e:
            logger.debug(f"  {source_name} error: {e}")
            continue

    if not pdf_url:
        logger.info(f"  No PDF URL found")
        return None, None

    # Download PDF
    safe_title = re.sub(r'[^\w\s-]', '', title[:50])
    pdf_filename = f"{safe_title}_{openalex_work_id}.pdf"
    pdf_path = PDF_CACHE_DIR / pdf_filename

    if not download_pdf(pdf_url, pdf_path):
        return None, pdf_url

    # Extract text
    pdf_text = extract_text_from_pdf(pdf_path)

    # Clean up PDF file (optional - comment out to keep PDFs)
    try:
        pdf_path.unlink()
    except:
        pass

    if pdf_text:
        return pdf_text, pdf_url
    else:
        return None, pdf_url


def create_enhanced_document(faculty: Dict, publication: Dict, pdf_text: Optional[str],
                            pdf_url: Optional[str], access_status: str) -> str:
    """
    Create enhanced document text with full PDF content

    Args:
        faculty: Faculty dictionary
        publication: Publication dictionary
        pdf_text: Full text extracted from PDF (if available)
        pdf_url: PDF URL if found
        access_status: 'full_text', 'paywall', or 'not_found'

    Returns:
        Enhanced document text for ChromaDB
    """
    doc = f"Faculty: {faculty['name']}\n"
    doc += f"Department: {faculty['department']}\n"
    doc += f"OpenAlex ID: {faculty['openalex_id']}\n\n"

    doc += f"Publication Title: {publication['title']}\n"
    doc += f"Year: {publication['publication_year']}\n"
    doc += f"Type: {publication['type']}\n"

    if publication.get('doi'):
        doc += f"DOI: {publication['doi']}\n"

    if publication.get('primary_location'):
        doc += f"Published in: {publication['primary_location']}\n"

    doc += f"Citations: {publication['cited_by_count']}\n"
    doc += f"Open Access: {'Yes' if publication['is_open_access'] else 'No'}\n"

    # Add access status information
    if access_status == 'full_text':
        doc += f"Access Status: Full text available\n"
    elif access_status == 'paywall':
        doc += f"Access Status: BEHIND PAYWALL - Full text not accessible\n"
        if pdf_url:
            doc += f"Publisher URL: {pdf_url}\n"
        doc += f"Note: This publication requires institutional access or purchase to view the full text.\n"
    else:  # not_found
        doc += f"Access Status: Full text not found - Metadata only\n"
        if publication.get('is_open_access'):
            doc += f"Note: Marked as open access but PDF location unknown. May require manual search.\n"
        else:
            doc += f"Note: Likely behind paywall or not digitally available.\n"

    doc += "\n" + "="*80 + "\n\n"

    if pdf_text:
        doc += "FULL PAPER TEXT:\n\n"
        doc += pdf_text
    elif access_status == 'paywall':
        doc += "FULL TEXT UNAVAILABLE - BEHIND PAYWALL\n\n"
        doc += "This paper is published in a subscription journal and requires institutional access or purchase.\n"
        doc += "Only metadata is available for searching and reference.\n"
        if publication.get('doi'):
            doc += f"\nTo access the full paper, visit: {publication['doi']}\n"
    else:
        doc += "FULL TEXT UNAVAILABLE\n\n"
        doc += "The full text of this paper could not be located in open access repositories.\n"
        doc += "Only metadata is available for searching and reference.\n"

    return doc


def update_database_with_pdfs(input_file: str, db_manager: ChromaDBManager):
    """
    Load publications and update ChromaDB with full PDF content

    Args:
        input_file: Path to filtered faculty JSON
        db_manager: ChromaDB manager instance
    """
    print("="*80)
    print("DOWNLOADING AND EXTRACTING FULL PDF CONTENT")
    print("="*80)

    # Load faculty data
    print(f"\nLoading faculty from: {input_file}")

    with open(input_file, 'r', encoding='utf-8') as f:
        faculty_list = json.load(f)

    print(f"Loaded {len(faculty_list)} faculty members")

    # Statistics
    total_publications = 0
    pdfs_found = 0
    pdfs_extracted = 0
    behind_paywall = 0
    not_found = 0

    print("\n" + "="*80)
    print("PROCESSING PUBLICATIONS")
    print("="*80)
    print()

    documents = []
    metadatas = []
    ids = []

    for i, faculty in enumerate(faculty_list, 1):
        name = faculty['name']
        dept = faculty['department']
        pubs = faculty.get('publications_2020_plus', [])

        if not pubs:
            continue

        # Safe printing
        safe_name = name.encode('ascii', errors='replace').decode('ascii')
        safe_dept = dept.encode('ascii', errors='replace').decode('ascii')

        try:
            print(f"\n[{i}/{len(faculty_list)}] {name} ({dept}) - {len(pubs)} publications")
        except UnicodeEncodeError:
            print(f"\n[{i}/{len(faculty_list)}] {safe_name} ({safe_dept}) - {len(pubs)} publications")

        for j, pub in enumerate(pubs, 1):
            total_publications += 1

            # Safe printing for publication titles
            title = pub.get('title', 'Untitled')[:60]
            safe_title = title.encode('ascii', errors='replace').decode('ascii')
            try:
                print(f"  [{j}/{len(pubs)}] {title}...")
            except UnicodeEncodeError:
                print(f"  [{j}/{len(pubs)}] {safe_title}...")

            # Try to find and extract PDF
            pdf_text, pdf_url = find_and_extract_pdf(pub, faculty)

            # Determine access status
            if pdf_text:
                access_status = 'full_text'
                pdfs_extracted += 1
                print(f"  [OK] Extracted full text ({len(pdf_text)} chars)")
            elif pdf_url and not pdf_text:
                # PDF URL found but extraction failed - likely paywall or broken link
                access_status = 'paywall'
                behind_paywall += 1
                print(f"  [PAYWALL] Behind paywall or extraction failed")
            else:
                # No PDF found at all
                access_status = 'not_found'
                not_found += 1
                if pub.get('is_open_access'):
                    print(f"  [WARNING] Marked as OA but PDF not found")
                else:
                    print(f"  [NOT FOUND] No open access version found")

            if pdf_url:
                pdfs_found += 1

            # Create enhanced document with access status
            doc_text = create_enhanced_document(faculty, pub, pdf_text, pdf_url, access_status)

            # Create metadata with access status
            metadata = {
                'faculty_name': name or 'Unknown',
                'department': dept or 'Unknown',
                'content_type': 'Publication',
                'date_published': pub.get('publication_date') or f"{pub.get('publication_year', 2020)}-01-01",
                'publication_year': int(pub.get('publication_year') or 2020),
                'publication_title': pub.get('title') or 'Untitled',
                'doi': pub.get('doi') or '',
                'openalex_id': faculty.get('openalex_id') or '',
                'openalex_work_id': pub.get('id') or '',
                'cited_by_count': int(pub.get('cited_by_count') or 0),
                'is_open_access': bool(pub.get('is_open_access', False)),
                'pdf_url': pdf_url or '',
                'has_full_text': bool(pdf_text),
                'access_status': access_status  # 'full_text', 'paywall', or 'not_found'
            }

            # Create unique ID
            doc_id = f"pub_{faculty['openalex_id']}_{pub['id']}"

            documents.append(doc_text)
            metadatas.append(metadata)
            ids.append(doc_id)

            # Add in batches of 50 (smaller batches for large text)
            if len(documents) >= 50:
                print(f"\n  Updating database batch ({len(documents)} documents)...")
                db_manager.collection.upsert(documents=documents, metadatas=metadatas, ids=ids)
                print(f"Successfully upserted {len(documents)} documents to collection 'faculty_pulse'")
                documents = []
                metadatas = []
                ids = []

            # Rate limiting
            time.sleep(0.5)

    # Add remaining documents
    if documents:
        print(f"\n  Updating database final batch ({len(documents)} documents)...")
        db_manager.collection.upsert(documents=documents, metadatas=metadatas, ids=ids)
        print(f"Successfully upserted {len(documents)} documents to collection 'faculty_pulse'")

    print("\n" + "="*80)
    print("PDF EXTRACTION SUMMARY")
    print("="*80)
    print(f"Total publications: {total_publications}")
    print(f"\nAccess Status Breakdown:")
    print(f"  [OK] Full text extracted: {pdfs_extracted} ({pdfs_extracted/total_publications*100:.1f}%)")
    print(f"  [PAYWALL] Behind paywall: {behind_paywall} ({behind_paywall/total_publications*100:.1f}%)")
    print(f"  [NOT FOUND] Not found: {not_found} ({not_found/total_publications*100:.1f}%)")
    print(f"\nPDF URLs found: {pdfs_found} ({pdfs_found/total_publications*100:.1f}%)")
    print("="*80)

    # Database statistics
    print("\nDatabase Statistics:")
    total_docs = db_manager.get_collection_count()
    print(f"Total documents in database: {total_docs}")


def main():
    """Main execution"""
    print("\n" + "="*80)
    print("FACULTY PUBLICATIONS - FULL PDF CONTENT EXTRACTION")
    print("="*80)
    print("\nThis script will:")
    print("  1. Try to find open access PDFs for each publication")
    print("  2. Download and extract full text from PDFs")
    print("  3. Update ChromaDB with complete paper content")
    print("  4. Fall back to metadata-only if PDF unavailable")
    print()
    print("Sources: Unpaywall, OpenAlex, arXiv")
    print("="*80)

    # Input file
    input_file = "haverford_faculty_filtered_no_history.json"

    if not os.path.exists(input_file):
        print(f"ERROR: Input file not found: {input_file}")
        return

    # Check for pypdf
    try:
        import pypdf
    except ImportError:
        print("\nERROR: pypdf library not installed")
        print("Please install it with: pip install pypdf")
        return

    # Initialize ChromaDB manager
    print("\nInitializing ChromaDB connection...")
    db_manager = ChromaDBManager(
        persist_directory="./chroma_db",
        collection_name="faculty_pulse"
    )

    print(f"Connected to collection: {db_manager.collection_name}")
    print(f"Current document count: {db_manager.get_collection_count()}")

    print("\n" + "="*80)
    print("Starting PDF extraction and database update...")
    print("This may take 30-60 minutes for 228 publications.")
    print("Papers behind paywalls will be marked appropriately.")
    print("="*80)

    # Update database with PDF content
    update_database_with_pdfs(input_file, db_manager)

    print("\n[OK] PDF extraction and database update complete!")
    print("\nYour chatbot now has access to:")
    print("  - Full text content from open access papers")
    print("  - Publication metadata for all papers")
    print("  - Direct PDF URLs where available")
    print("\nThe AI can now read and summarize the actual research papers!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
