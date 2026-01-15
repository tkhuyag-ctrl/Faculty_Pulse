"""
Download PDFs and Update Existing Publications in ChromaDB
- Fetches existing publications from ChromaDB
- Downloads PDFs from Unpaywall, OpenAlex, arXiv, and scholarship repository
- Extracts full text and updates database
- Then runs RAG chunking for large documents
"""
import json
import requests
import time
import logging
import os
import re
from typing import Optional, Tuple
from pathlib import Path
import pypdf
from chroma_manager import ChromaDBManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('pdf_download_existing.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

# Create PDF cache directory
PDF_CACHE_DIR = Path("./pdf_cache")
PDF_CACHE_DIR.mkdir(exist_ok=True)


def clean_text(text: str) -> str:
    """Clean extracted text from PDFs"""
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n\d+\n', '\n', text)
    return text.strip()


def try_unpaywall_pdf(doi: str) -> Optional[str]:
    """Try to get PDF URL from Unpaywall API"""
    if not doi:
        return None

    try:
        clean_doi = doi.replace('https://doi.org/', '').strip()
        if not clean_doi:
            return None

        email = "research@example.com"
        url = f"https://api.unpaywall.org/v2/{clean_doi}?email={email}"

        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('is_oa'):
                best_oa = data.get('best_oa_location', {})
                pdf_url = best_oa.get('url_for_pdf')
                if pdf_url:
                    logger.info(f"    Unpaywall: Found PDF")
                    return pdf_url

        return None

    except Exception as e:
        logger.debug(f"    Unpaywall failed: {e}")
        return None


def try_openalex_pdf(openalex_work_id: str) -> Optional[str]:
    """Try to get PDF URL from OpenAlex"""
    if not openalex_work_id:
        return None

    try:
        # Handle both full URLs and IDs
        if openalex_work_id.startswith('http'):
            url = openalex_work_id
        else:
            # Clean ID
            clean_id = openalex_work_id.replace('https://openalex.org/', '').strip()
            url = f"https://api.openalex.org/works/{clean_id}"

        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()

            # Check all locations for PDF
            locations = data.get('locations', [])
            for location in locations:
                pdf_url = location.get('pdf_url')
                if pdf_url:
                    logger.info(f"    OpenAlex: Found PDF")
                    return pdf_url

            # Check primary location
            primary = data.get('primary_location', {})
            if primary:
                pdf_url = primary.get('pdf_url')
                if pdf_url:
                    logger.info(f"    OpenAlex primary: Found PDF")
                    return pdf_url

        return None

    except Exception as e:
        logger.debug(f"    OpenAlex failed: {e}")
        return None


def try_arxiv_pdf(title: str) -> Optional[str]:
    """Try to find paper on arXiv"""
    if not title:
        return None

    try:
        search_url = "http://export.arxiv.org/api/query"
        params = {
            'search_query': f'ti:"{title}"',
            'max_results': 1
        }

        response = requests.get(search_url, params=params, timeout=10)

        if response.status_code == 200 and 'arxiv.org/abs/' in response.text:
            match = re.search(r'arxiv\.org/abs/(\d+\.\d+)', response.text)
            if match:
                arxiv_id = match.group(1)
                pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
                logger.info(f"    arXiv: Found PDF")
                return pdf_url

        return None

    except Exception as e:
        logger.debug(f"    arXiv failed: {e}")
        return None


def download_pdf(pdf_url: str, output_path: Path) -> bool:
    """Download PDF from URL"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(pdf_url, headers=headers, timeout=30, stream=True)

        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info(f"    Downloaded PDF ({output_path.stat().st_size} bytes)")
            return True
        else:
            logger.warning(f"    Download failed: HTTP {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"    Download error: {e}")
        return False


def extract_text_from_pdf(pdf_path: Path) -> Optional[str]:
    """Extract text from PDF"""
    try:
        with open(pdf_path, 'rb') as f:
            pdf_reader = pypdf.PdfReader(f)
            num_pages = len(pdf_reader.pages)

            text_parts = []
            for i, page in enumerate(pdf_reader.pages):
                try:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
                except Exception as e:
                    logger.warning(f"    Failed to extract page {i+1}: {e}")
                    continue

            if text_parts:
                full_text = "\n\n".join(text_parts)
                full_text = clean_text(full_text)
                word_count = len(full_text.split())
                logger.info(f"    Extracted {word_count:,} words from {num_pages} pages")
                return full_text

        return None

    except Exception as e:
        logger.error(f"    PDF extraction error: {e}")
        return None


def find_and_download_pdf(title: str, doi: str, openalex_work_id: str, venue: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Try multiple sources to find and extract PDF

    Returns:
        Tuple of (pdf_text, pdf_url) if successful
    """
    logger.info(f"    Searching for PDF...")

    # Try multiple sources
    pdf_url = None
    sources = [
        ('OpenAlex', lambda: try_openalex_pdf(openalex_work_id)),
        ('Unpaywall', lambda: try_unpaywall_pdf(doi)),
        ('arXiv', lambda: try_arxiv_pdf(title))
    ]

    for source_name, source_func in sources:
        try:
            pdf_url = source_func()
            if pdf_url:
                break
            time.sleep(0.2)
        except Exception as e:
            logger.debug(f"    {source_name} error: {e}")
            continue

    if not pdf_url:
        logger.info(f"    No PDF URL found")
        return None, None

    # Download PDF
    safe_title = re.sub(r'[^\w\s-]', '', title[:30])
    pdf_filename = f"{safe_title}.pdf"
    pdf_path = PDF_CACHE_DIR / pdf_filename

    if not download_pdf(pdf_url, pdf_path):
        return None, pdf_url

    # Extract text
    pdf_text = extract_text_from_pdf(pdf_path)

    # Keep PDF file for reference
    # Uncomment to delete: pdf_path.unlink()

    if pdf_text:
        return pdf_text, pdf_url
    else:
        return None, pdf_url


def update_existing_publications():
    """Main function to update existing publications with PDFs"""
    print("="*80)
    print("DOWNLOAD PDFs FOR EXISTING PUBLICATIONS")
    print("="*80)
    print()

    # Connect to ChromaDB
    print("Connecting to ChromaDB...")
    db_manager = ChromaDBManager(
        persist_directory="./chroma_db",
        collection_name="faculty_pulse"
    )

    print(f"Connected to collection: {db_manager.collection_name}")

    # Get all publications
    print("Fetching existing publications...")
    all_docs = db_manager.get_all_submissions()

    total_docs = len(all_docs['ids'])
    print(f"Total documents: {total_docs}")

    # Filter for publications without full text
    publications = []
    for doc_id, doc_text, metadata in zip(all_docs['ids'], all_docs['documents'], all_docs['metadatas']):
        if metadata.get('content_type') == 'Publication':
            # Check if it already has full PDF text
            has_full_text = metadata.get('has_full_text', False)
            if not has_full_text and 'FULL PAPER TEXT:' not in doc_text:
                publications.append({
                    'id': doc_id,
                    'text': doc_text,
                    'metadata': metadata
                })

    print(f"Publications without full text: {len(publications)}")
    print()

    if not publications:
        print("All publications already have full text!")
        return

    # Process publications
    print("="*80)
    print(f"PROCESSING {len(publications)} PUBLICATIONS")
    print("="*80)
    print()

    stats = {
        'processed': 0,
        'pdfs_found': 0,
        'pdfs_extracted': 0,
        'failed': 0
    }

    for i, pub_data in enumerate(publications, 1):
        doc_id = pub_data['id']
        metadata = pub_data['metadata']
        doc_text = pub_data['text']

        title = metadata.get('title', metadata.get('publication_title', 'Untitled'))[:60]
        faculty_name = metadata.get('author', metadata.get('faculty_name', 'Unknown'))

        # Handle unicode characters in print
        safe_title = title.encode('ascii', errors='replace').decode('ascii')
        safe_faculty = faculty_name.encode('ascii', errors='replace').decode('ascii')
        print(f"[{i}/{len(publications)}] {safe_faculty}: {safe_title}...")

        # Extract metadata
        doi = metadata.get('doi', '')
        openalex_work_id = metadata.get('openalex_work_id', '')
        venue = metadata.get('venue', '')

        # Try to find and download PDF
        pdf_text, pdf_url = find_and_download_pdf(title, doi, openalex_work_id, venue)

        stats['processed'] += 1

        if pdf_text:
            # Update document with full text
            enhanced_doc = doc_text + "\n\n" + "="*80 + "\n\nFULL PAPER TEXT:\n\n" + pdf_text

            # Update metadata
            updated_metadata = metadata.copy()
            updated_metadata['has_full_text'] = True
            updated_metadata['pdf_url'] = pdf_url
            updated_metadata['access_status'] = 'full_text'

            # Update in database
            db_manager.collection.update(
                ids=[doc_id],
                documents=[enhanced_doc],
                metadatas=[updated_metadata]
            )

            stats['pdfs_extracted'] += 1
            print(f"  SUCCESS: Added full text ({len(pdf_text):,} chars)")

        elif pdf_url:
            # PDF found but extraction failed
            updated_metadata = metadata.copy()
            updated_metadata['pdf_url'] = pdf_url
            updated_metadata['access_status'] = 'paywall'

            db_manager.collection.update(
                ids=[doc_id],
                metadatas=[updated_metadata]
            )

            stats['pdfs_found'] += 1
            stats['failed'] += 1
            print(f"  PARTIAL: PDF found but extraction failed")

        else:
            # No PDF found
            updated_metadata = metadata.copy()
            updated_metadata['access_status'] = 'not_found'

            db_manager.collection.update(
                ids=[doc_id],
                metadatas=[updated_metadata]
            )

            stats['failed'] += 1
            print(f"  NOT FOUND: No PDF available")

        # Rate limiting
        time.sleep(0.5)

    # Summary
    print("\n" + "="*80)
    print("PDF DOWNLOAD SUMMARY")
    print("="*80)
    print(f"Publications processed: {stats['processed']}")
    print(f"PDFs extracted: {stats['pdfs_extracted']} ({stats['pdfs_extracted']/stats['processed']*100:.1f}%)")
    print(f"PDFs found but not extracted: {stats['pdfs_found']}")
    print(f"No PDF found: {stats['failed'] - stats['pdfs_found']}")
    print("="*80)
    print()

    # Now run RAG chunking for large documents
    if stats['pdfs_extracted'] > 0:
        print("\n" + "="*80)
        print("RUNNING RAG CHUNKING FOR LARGE DOCUMENTS")
        print("="*80)
        print()

        from implement_rag_chunking import chunk_large_documents

        chunk_large_documents(
            db_manager=db_manager,
            threshold_words=50000,
            chunk_size=2000,
            overlap=200
        )

    print("\nDONE! Your database now has:")
    print("  - Full PDF text where available")
    print("  - Large documents chunked for RAG")
    print("  - Enhanced metadata with access status")


if __name__ == "__main__":
    try:
        update_existing_publications()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
