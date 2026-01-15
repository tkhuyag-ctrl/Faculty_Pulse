"""
Automated Publication Processing Pipeline

This script automatically processes new publications from any source through:
1. PDF extraction (with paywall detection)
2. RAG chunking (if needed)
3. Access status labeling
4. ChromaDB integration

Sources supported:
- OpenAlex API
- Haverford Scholarship website
- Manual JSON imports
- Any custom source

Usage:
    python auto_process_publications.py

Or import and use programmatically:
    from auto_process_publications import process_new_publications
    process_new_publications(publications_data)
"""

import json
import logging
import time
from typing import List, Dict, Optional
from pathlib import Path

from chroma_manager import ChromaDBManager
from download_and_extract_pdfs import (
    find_and_extract_pdf,
    create_enhanced_document
)
from implement_rag_chunking import chunk_text, extract_paper_content

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('auto_process.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


class PublicationProcessor:
    """
    Automated processor for new publications from any source
    """

    def __init__(self,
                 db_manager: ChromaDBManager = None,
                 rag_threshold_words: int = 50000,
                 rag_chunk_size: int = 2000,
                 rag_overlap: int = 200):
        """
        Initialize the publication processor

        Args:
            db_manager: ChromaDB manager instance (creates new if None)
            rag_threshold_words: Chunk documents larger than this
            rag_chunk_size: Words per chunk
            rag_overlap: Overlap between chunks
        """
        self.db_manager = db_manager or ChromaDBManager(
            persist_directory="./chroma_db",
            collection_name="faculty_pulse"
        )
        self.rag_threshold = rag_threshold_words
        self.rag_chunk_size = rag_chunk_size
        self.rag_overlap = rag_overlap

        logger.info("Publication processor initialized")
        logger.info(f"Database: {self.db_manager.collection_name}")
        logger.info(f"Current document count: {self.db_manager.get_collection_count()}")

    def process_single_publication(self,
                                  publication: Dict,
                                  faculty: Dict,
                                  skip_existing: bool = True) -> bool:
        """
        Process a single publication through the full pipeline

        Args:
            publication: Publication data dictionary
            faculty: Faculty data dictionary
            skip_existing: Skip if already in database

        Returns:
            True if processed successfully, False otherwise
        """
        try:
            # Create document ID
            doc_id = f"pub_{faculty.get('openalex_id', 'unknown')}_{publication.get('id', 'unknown')}"

            # Check if already exists
            if skip_existing:
                existing = self.db_manager.collection.get(ids=[doc_id])
                if existing['ids']:
                    logger.info(f"Skipping existing publication: {publication.get('title', 'Untitled')[:60]}")
                    return True

            title = publication.get('title', 'Untitled')[:60]
            logger.info(f"Processing: {title}...")

            # Step 1: Extract PDF and determine access status
            pdf_text, pdf_url = find_and_extract_pdf(publication, faculty)

            if pdf_text:
                access_status = 'full_text'
                logger.info(f"  [OK] Extracted full text ({len(pdf_text)} chars)")
            elif pdf_url and not pdf_text:
                access_status = 'paywall'
                logger.info(f"  [PAYWALL] Behind paywall or extraction failed")
            else:
                access_status = 'not_found'
                logger.info(f"  [NOT FOUND] No open access version found")

            # Step 2: Create enhanced document with access status
            doc_text = create_enhanced_document(faculty, publication, pdf_text, pdf_url, access_status)

            # Step 3: Check if RAG chunking is needed
            if pdf_text:
                word_count = len(pdf_text.split())

                if word_count > self.rag_threshold:
                    logger.info(f"  [RAG] Document has {word_count:,} words - chunking required")
                    return self._process_with_chunking(
                        doc_id, doc_text, publication, faculty, pdf_text, pdf_url, access_status
                    )

            # Step 4: Create metadata with access status
            metadata = self._create_metadata(publication, faculty, pdf_text, pdf_url, access_status)

            # Step 5: Add to database
            self.db_manager.collection.upsert(
                documents=[doc_text],
                metadatas=[metadata],
                ids=[doc_id]
            )

            logger.info(f"  [SUCCESS] Added to database: {doc_id}")
            return True

        except Exception as e:
            logger.error(f"Error processing publication: {e}")
            return False

    def _process_with_chunking(self,
                              doc_id: str,
                              doc_text: str,
                              publication: Dict,
                              faculty: Dict,
                              pdf_text: str,
                              pdf_url: str,
                              access_status: str) -> bool:
        """
        Process a large document with RAG chunking

        Args:
            doc_id: Document ID
            doc_text: Full enhanced document text
            publication: Publication data
            faculty: Faculty data
            pdf_text: Extracted PDF text
            pdf_url: PDF URL
            access_status: Access status

        Returns:
            True if successful
        """
        try:
            # Extract metadata header and paper content
            metadata_header, paper_content = extract_paper_content(doc_text)

            if not paper_content:
                logger.warning("  [RAG] No paper content to chunk")
                return False

            # Chunk the paper content
            chunks = chunk_text(
                paper_content,
                chunk_size=self.rag_chunk_size,
                overlap=self.rag_overlap
            )

            logger.info(f"  [RAG] Creating {len(chunks)} chunks...")

            # Create chunked documents
            chunk_docs = []
            chunk_metas = []
            chunk_ids = []

            base_metadata = self._create_metadata(publication, faculty, pdf_text, pdf_url, access_status)

            for chunk_idx, chunk in enumerate(chunks, 1):
                # Reconstruct document with metadata header + chunk
                chunk_doc = f"{metadata_header}\n\n{'='*80}\n\nFULL PAPER TEXT (Chunk {chunk_idx}/{len(chunks)}):\n\n{chunk}"

                # Copy metadata and add chunk info
                chunk_meta = base_metadata.copy()
                chunk_meta['chunk_index'] = chunk_idx
                chunk_meta['total_chunks'] = len(chunks)
                chunk_meta['is_chunked'] = True

                # Create unique chunk ID
                chunk_id = f"{doc_id}_chunk_{chunk_idx}"

                chunk_docs.append(chunk_doc)
                chunk_metas.append(chunk_meta)
                chunk_ids.append(chunk_id)

            # Upsert all chunks
            self.db_manager.collection.upsert(
                documents=chunk_docs,
                metadatas=chunk_metas,
                ids=chunk_ids
            )

            logger.info(f"  [RAG SUCCESS] Added {len(chunks)} chunks to database")
            return True

        except Exception as e:
            logger.error(f"  [RAG ERROR] Chunking failed: {e}")
            return False

    def _create_metadata(self,
                        publication: Dict,
                        faculty: Dict,
                        pdf_text: Optional[str],
                        pdf_url: Optional[str],
                        access_status: str) -> Dict:
        """
        Create metadata dictionary for ChromaDB

        Args:
            publication: Publication data
            faculty: Faculty data
            pdf_text: Extracted PDF text (if available)
            pdf_url: PDF URL (if available)
            access_status: 'full_text', 'paywall', or 'not_found'

        Returns:
            Metadata dictionary
        """
        return {
            'faculty_name': faculty.get('name') or 'Unknown',
            'department': faculty.get('department') or 'Unknown',
            'content_type': 'Publication',
            'date_published': publication.get('publication_date') or f"{publication.get('publication_year', 2020)}-01-01",
            'publication_year': int(publication.get('publication_year') or 2020),
            'publication_title': publication.get('title') or 'Untitled',
            'doi': publication.get('doi') or '',
            'openalex_id': faculty.get('openalex_id') or '',
            'openalex_work_id': publication.get('id') or '',
            'cited_by_count': int(publication.get('cited_by_count') or 0),
            'is_open_access': bool(publication.get('is_open_access', False)),
            'pdf_url': pdf_url or '',
            'has_full_text': bool(pdf_text),
            'access_status': access_status,  # 'full_text', 'paywall', or 'not_found'
            'source': publication.get('source', 'unknown')  # Track where it came from
        }

    def process_publications_batch(self,
                                  publications: List[Dict],
                                  faculty_info: Dict,
                                  skip_existing: bool = True) -> Dict:
        """
        Process a batch of publications

        Args:
            publications: List of publication dictionaries
            faculty_info: Faculty information dictionary
            skip_existing: Skip publications already in database

        Returns:
            Dictionary with processing statistics
        """
        stats = {
            'total': len(publications),
            'processed': 0,
            'full_text': 0,
            'paywall': 0,
            'not_found': 0,
            'chunked': 0,
            'failed': 0
        }

        logger.info(f"\n{'='*80}")
        logger.info(f"PROCESSING BATCH: {len(publications)} publications")
        logger.info(f"Faculty: {faculty_info.get('name', 'Unknown')}")
        logger.info(f"{'='*80}\n")

        for i, pub in enumerate(publications, 1):
            logger.info(f"[{i}/{len(publications)}] Processing...")

            success = self.process_single_publication(pub, faculty_info, skip_existing)

            if success:
                stats['processed'] += 1

                # Check what was added
                doc_id = f"pub_{faculty_info.get('openalex_id', 'unknown')}_{pub.get('id', 'unknown')}"
                result = self.db_manager.collection.get(ids=[doc_id], include=['metadatas'])

                if result['metadatas']:
                    meta = result['metadatas'][0]
                    access_status = meta.get('access_status', 'unknown')

                    if access_status == 'full_text':
                        stats['full_text'] += 1
                    elif access_status == 'paywall':
                        stats['paywall'] += 1
                    elif access_status == 'not_found':
                        stats['not_found'] += 1

                    if meta.get('is_chunked', False):
                        stats['chunked'] += 1
            else:
                stats['failed'] += 1

            # Rate limiting
            time.sleep(0.5)

        # Print summary
        logger.info(f"\n{'='*80}")
        logger.info("BATCH PROCESSING COMPLETE")
        logger.info(f"{'='*80}")
        logger.info(f"Total: {stats['total']}")
        logger.info(f"Processed: {stats['processed']}")
        logger.info(f"  - Full text: {stats['full_text']}")
        logger.info(f"  - Paywall: {stats['paywall']}")
        logger.info(f"  - Not found: {stats['not_found']}")
        logger.info(f"  - Chunked: {stats['chunked']}")
        logger.info(f"Failed: {stats['failed']}")
        logger.info(f"{'='*80}\n")

        return stats

    def process_from_json_file(self, json_file: str, skip_existing: bool = True) -> Dict:
        """
        Process publications from a JSON file

        Args:
            json_file: Path to JSON file with faculty/publications data
            skip_existing: Skip publications already in database

        Returns:
            Dictionary with processing statistics
        """
        logger.info(f"Loading publications from: {json_file}")

        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Handle different JSON formats
        if isinstance(data, list):
            # List of faculty members
            faculty_list = data
        elif isinstance(data, dict) and 'faculty' in data:
            # Dictionary with faculty key
            faculty_list = data['faculty']
        else:
            # Single faculty member
            faculty_list = [data]

        all_stats = {
            'total': 0,
            'processed': 0,
            'full_text': 0,
            'paywall': 0,
            'not_found': 0,
            'chunked': 0,
            'failed': 0
        }

        for faculty in faculty_list:
            pubs = faculty.get('publications_2020_plus', [])

            if not pubs:
                continue

            stats = self.process_publications_batch(pubs, faculty, skip_existing)

            # Aggregate statistics
            for key in all_stats:
                all_stats[key] += stats.get(key, 0)

        logger.info(f"\n{'='*80}")
        logger.info("FILE PROCESSING COMPLETE")
        logger.info(f"{'='*80}")
        logger.info(f"Total publications: {all_stats['total']}")
        logger.info(f"Successfully processed: {all_stats['processed']}")
        logger.info(f"  - Full text: {all_stats['full_text']}")
        logger.info(f"  - Paywall: {all_stats['paywall']}")
        logger.info(f"  - Not found: {all_stats['not_found']}")
        logger.info(f"  - Chunked: {all_stats['chunked']}")
        logger.info(f"Failed: {all_stats['failed']}")
        logger.info(f"{'='*80}\n")

        return all_stats


def process_new_publications(publications_data,
                            faculty_info: Dict = None,
                            skip_existing: bool = True) -> Dict:
    """
    Main entry point for processing new publications

    Args:
        publications_data: Can be:
            - List of publication dictionaries
            - Path to JSON file (str)
            - Dictionary with publications
        faculty_info: Faculty information (required if publications_data is a list)
        skip_existing: Skip publications already in database

    Returns:
        Dictionary with processing statistics
    """
    processor = PublicationProcessor()

    # Handle different input types
    if isinstance(publications_data, str):
        # File path
        return processor.process_from_json_file(publications_data, skip_existing)

    elif isinstance(publications_data, list):
        # List of publications
        if not faculty_info:
            raise ValueError("faculty_info is required when publications_data is a list")
        return processor.process_publications_batch(publications_data, faculty_info, skip_existing)

    elif isinstance(publications_data, dict):
        # Could be single faculty or single publication
        if 'publications_2020_plus' in publications_data:
            # Single faculty member
            pubs = publications_data['publications_2020_plus']
            return processor.process_publications_batch(pubs, publications_data, skip_existing)
        else:
            # Single publication
            if not faculty_info:
                raise ValueError("faculty_info is required for single publication")
            processor.process_single_publication(publications_data, faculty_info, skip_existing)
            return {'total': 1, 'processed': 1}

    else:
        raise ValueError(f"Unsupported publications_data type: {type(publications_data)}")


def main():
    """
    Main execution - process default faculty file
    """
    print("\n" + "="*80)
    print("AUTOMATED PUBLICATION PROCESSING PIPELINE")
    print("="*80)
    print("\nThis script automatically processes publications through:")
    print("  1. PDF extraction with multi-source discovery")
    print("  2. Paywall detection and labeling")
    print("  3. RAG chunking for large documents (>50K words)")
    print("  4. ChromaDB integration with full metadata")
    print("\nSupported sources:")
    print("  - OpenAlex API")
    print("  - Haverford Scholarship website")
    print("  - Manual JSON imports")
    print("  - Any custom source")
    print("="*80)
    print()

    # Process the default faculty file
    input_file = "haverford_faculty_filtered_no_history.json"

    if not Path(input_file).exists():
        print(f"Error: File not found: {input_file}")
        return

    stats = process_new_publications(input_file, skip_existing=True)

    print("\n" + "="*80)
    print("PIPELINE COMPLETE")
    print("="*80)
    print("\nYour Faculty Pulse database is up to date!")
    print("New publications from any source will be automatically:")
    print("  - Extracted (if accessible)")
    print("  - Labeled (paywall status)")
    print("  - Chunked (if needed)")
    print("  - Searchable (in ChromaDB)")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
