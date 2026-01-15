"""
Integrate Haverford Faculty Data (excluding History) into Faculty Pulse Chatbot
- Loads faculty with OpenAlex IDs and 2020+ publications
- Fetches publication PDFs where available
- Stores everything in ChromaDB for chatbot queries
"""
import json
import requests
import time
import logging
from typing import List, Dict, Optional
from chroma_manager import ChromaDBManager
from datetime import datetime
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('integration.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


def fetch_pdf_url(doi: str) -> Optional[str]:
    """
    Try to fetch PDF URL from Unpaywall API using DOI

    Args:
        doi: DOI of the publication

    Returns:
        PDF URL if available, None otherwise
    """
    if not doi:
        return None

    try:
        # Clean DOI - remove https://doi.org/ prefix if present
        clean_doi = doi.replace('https://doi.org/', '')

        # Unpaywall API
        email = "research@example.com"  # Change to your email
        url = f"https://api.unpaywall.org/v2/{clean_doi}?email={email}"

        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            data = response.json()

            # Check for open access PDF
            if data.get('is_oa'):
                best_oa = data.get('best_oa_location', {})
                pdf_url = best_oa.get('url_for_pdf')

                if pdf_url:
                    logger.info(f"  Found open access PDF for {clean_doi}")
                    return pdf_url

        return None

    except Exception as e:
        logger.debug(f"  Could not fetch PDF for {doi}: {e}")
        return None


def create_document_text(faculty: Dict, publication: Dict) -> str:
    """
    Create searchable document text for a publication

    Args:
        faculty: Faculty dictionary
        publication: Publication dictionary

    Returns:
        Formatted document text
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

    if publication.get('abstract'):
        doc += "\nNote: Abstract available in OpenAlex\n"

    return doc


def integrate_faculty_data(input_file: str, db_manager: ChromaDBManager):
    """
    Load faculty data and integrate into ChromaDB

    Args:
        input_file: Path to filtered faculty JSON
        db_manager: ChromaDB manager instance
    """
    print("="*80)
    print("INTEGRATING FACULTY DATA INTO CHATBOT")
    print("="*80)

    # Load faculty data
    print(f"\nLoading faculty from: {input_file}")

    with open(input_file, 'r', encoding='utf-8') as f:
        faculty_list = json.load(f)

    print(f"Loaded {len(faculty_list)} faculty members")

    # Statistics
    total_publications = 0
    publications_with_pdf = 0
    documents_added = 0

    print("\n" + "="*80)
    print("PROCESSING FACULTY AND PUBLICATIONS")
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

        # Safe printing for Windows console
        safe_name = name.encode('ascii', errors='replace').decode('ascii')
        safe_dept = dept.encode('ascii', errors='replace').decode('ascii')
        try:
            print(f"[{i}/{len(faculty_list)}] {name} ({dept}) - {len(pubs)} publications")
        except UnicodeEncodeError:
            print(f"[{i}/{len(faculty_list)}] {safe_name} ({safe_dept}) - {len(pubs)} publications")

        for j, pub in enumerate(pubs):
            total_publications += 1

            # Create document text
            doc_text = create_document_text(faculty, pub)

            # Try to fetch PDF URL if DOI exists
            pdf_url = None
            if pub.get('doi'):
                pdf_url = fetch_pdf_url(pub['doi'])
                if pdf_url:
                    publications_with_pdf += 1
                    doc_text += f"\nPDF URL: {pdf_url}\n"

            # Create metadata - ChromaDB doesn't accept None values
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
                'pdf_url': pdf_url or ''
            }

            # Create unique ID
            doc_id = f"pub_{faculty['openalex_id']}_{pub['id']}"

            documents.append(doc_text)
            metadatas.append(metadata)
            ids.append(doc_id)

            # Add in batches of 100
            if len(documents) >= 100:
                db_manager.add_documents(documents, metadatas, ids)
                documents_added += len(documents)
                documents = []
                metadatas = []
                ids = []

            # Rate limiting for PDF fetching
            time.sleep(0.1)

    # Add remaining documents
    if documents:
        db_manager.add_documents(documents, metadatas, ids)
        documents_added += len(documents)

    print("\n" + "="*80)
    print("INTEGRATION SUMMARY")
    print("="*80)
    print(f"Faculty processed: {len(faculty_list)}")
    print(f"Total publications: {total_publications}")
    print(f"Documents added to database: {documents_added}")
    print(f"Publications with PDF links: {publications_with_pdf}")
    print(f"PDF coverage: {publications_with_pdf/total_publications*100:.1f}%" if total_publications > 0 else "N/A")
    print("="*80)

    # Database statistics
    print("\nDatabase Statistics:")
    total_docs = db_manager.get_collection_count()
    print(f"Total documents in database: {total_docs}")


def main():
    """Main execution"""
    # Input file
    input_file = "haverford_faculty_filtered_no_history.json"

    if not os.path.exists(input_file):
        print(f"ERROR: Input file not found: {input_file}")
        print("Please run filter_exclude_history.py first")
        return

    # Initialize ChromaDB manager
    print("\nInitializing ChromaDB connection...")
    db_manager = ChromaDBManager(
        persist_directory="./chroma_db",
        collection_name="faculty_pulse"
    )

    print(f"Connected to collection: {db_manager.collection_name}")
    print(f"Current document count: {db_manager.get_collection_count()}")

    # Ask user for confirmation
    print("\n" + "="*80)
    print("WARNING: This will add faculty publication data to your database.")
    print("="*80)
    response = input("\nProceed with integration? (yes/no): ").strip().lower()

    if response != 'yes':
        print("Integration cancelled.")
        return

    # Integrate faculty data
    integrate_faculty_data(input_file, db_manager)

    print("\n✅ Integration complete!")
    print("\nYou can now use the chatbot to query faculty publications:")
    print("  - Ask about specific faculty research")
    print("  - Search by topic, year, or department")
    print("  - Get citation counts and open access status")
    print("  - Access PDF links for open access publications")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
