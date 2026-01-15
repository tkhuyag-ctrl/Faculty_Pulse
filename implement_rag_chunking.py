"""
Implement RAG (Retrieval-Augmented Generation) Chunking for Large Papers

This script:
1. Identifies large documents in ChromaDB that exceed context limits
2. Chunks them into manageable 2000-word segments with 200-word overlap
3. Re-adds chunked versions to the database
4. Preserves all metadata and access status information

Handles papers with 700K+ words by breaking them into searchable chunks.
"""
import logging
from typing import List, Dict
from chroma_manager import ChromaDBManager
import uuid

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('rag_chunking.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


def chunk_text(text: str, chunk_size: int = 2000, overlap: int = 200) -> List[str]:
    """
    Split text into overlapping chunks by word count

    Args:
        text: Text to chunk
        chunk_size: Number of words per chunk
        overlap: Number of words to overlap between chunks

    Returns:
        List of text chunks
    """
    words = text.split()

    if len(words) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunks.append(' '.join(chunk_words))

        # Move forward by (chunk_size - overlap) to create overlap
        start += (chunk_size - overlap)

        # Break if we've processed all words
        if end >= len(words):
            break

    return chunks


def extract_paper_content(document: str) -> tuple:
    """
    Extract metadata header and paper content from document

    Args:
        document: Full document text

    Returns:
        Tuple of (metadata_header, paper_content)
    """
    # Look for the separator that marks start of paper text
    separator = "="*80

    if separator in document:
        parts = document.split(separator, 1)
        metadata_header = parts[0].strip()

        if len(parts) > 1:
            paper_section = parts[1]

            # Extract actual paper text after "FULL PAPER TEXT:" marker
            if "FULL PAPER TEXT:" in paper_section:
                paper_content = paper_section.split("FULL PAPER TEXT:", 1)[1].strip()
            elif "FULL TEXT UNAVAILABLE" in paper_section:
                # No full text available - return empty
                paper_content = ""
            else:
                paper_content = paper_section.strip()

            return metadata_header, paper_content

    # Fallback: return as-is
    return document, ""


def chunk_large_documents(db_manager: ChromaDBManager,
                          threshold_words: int = 50000,
                          chunk_size: int = 2000,
                          overlap: int = 200):
    """
    Find large documents and chunk them for RAG

    Args:
        db_manager: ChromaDB manager instance
        threshold_words: Only chunk documents larger than this (in words)
        chunk_size: Words per chunk
        overlap: Overlap between chunks
    """
    print("="*80)
    print("IMPLEMENTING RAG CHUNKING FOR LARGE DOCUMENTS")
    print("="*80)
    print()

    # Get all documents
    print("Fetching all documents from database...")
    all_docs = db_manager.get_all_submissions()

    total_docs = len(all_docs['ids'])
    print(f"Total documents in database: {total_docs}")

    # Identify large documents that need chunking
    large_docs = []
    small_docs_count = 0

    print(f"\nAnalyzing documents (threshold: {threshold_words:,} words)...")

    for i, (doc_id, doc_text, metadata) in enumerate(zip(
        all_docs['ids'],
        all_docs['documents'],
        all_docs['metadatas']
    )):
        word_count = len(doc_text.split())

        if word_count > threshold_words:
            large_docs.append({
                'id': doc_id,
                'text': doc_text,
                'metadata': metadata,
                'word_count': word_count
            })
        else:
            small_docs_count += 1

    print(f"\nAnalysis Results:")
    print(f"  Small documents (< {threshold_words:,} words): {small_docs_count}")
    print(f"  Large documents (>= {threshold_words:,} words): {len(large_docs)}")

    if not large_docs:
        print("\nNo large documents found. RAG chunking not needed!")
        return

    # Show top 10 largest documents
    large_docs_sorted = sorted(large_docs, key=lambda x: x['word_count'], reverse=True)
    print(f"\nTop 10 Largest Documents:")
    for i, doc in enumerate(large_docs_sorted[:10], 1):
        title = doc['metadata'].get('publication_title', 'Unknown')[:60]
        words = doc['word_count']
        print(f"  {i}. {title}... - {words:,} words")

    # Process large documents
    print(f"\n{'='*80}")
    print(f"CHUNKING {len(large_docs)} LARGE DOCUMENTS")
    print(f"{'='*80}\n")

    chunks_created = 0
    total_chunks = 0

    for i, doc_data in enumerate(large_docs, 1):
        doc_id = doc_data['id']
        doc_text = doc_data['text']
        metadata = doc_data['metadata']
        word_count = doc_data['word_count']

        title = metadata.get('publication_title', 'Unknown')[:50]

        print(f"[{i}/{len(large_docs)}] {title}... ({word_count:,} words)")

        # Extract metadata header and paper content
        metadata_header, paper_content = extract_paper_content(doc_text)

        if not paper_content:
            print(f"  No paper content to chunk (metadata only)")
            continue

        # Chunk the paper content
        chunks = chunk_text(paper_content, chunk_size=chunk_size, overlap=overlap)

        print(f"  Creating {len(chunks)} chunks...")

        # Delete original large document
        try:
            db_manager.collection.delete(ids=[doc_id])
        except Exception as e:
            logger.warning(f"  Could not delete original doc {doc_id}: {e}")

        # Add chunked documents
        chunk_docs = []
        chunk_metas = []
        chunk_ids = []

        for chunk_idx, chunk in enumerate(chunks, 1):
            # Reconstruct document with metadata header + chunk
            chunk_doc = f"{metadata_header}\n\n{'='*80}\n\nFULL PAPER TEXT (Chunk {chunk_idx}/{len(chunks)}):\n\n{chunk}"

            # Copy metadata and add chunk info
            chunk_meta = metadata.copy()
            chunk_meta['chunk_index'] = chunk_idx
            chunk_meta['total_chunks'] = len(chunks)
            chunk_meta['is_chunked'] = True

            # Create unique chunk ID
            chunk_id = f"{doc_id}_chunk_{chunk_idx}"

            chunk_docs.append(chunk_doc)
            chunk_metas.append(chunk_meta)
            chunk_ids.append(chunk_id)

        # Add all chunks for this document
        db_manager.add_documents(chunk_docs, chunk_metas, chunk_ids)

        chunks_created += len(chunks)
        total_chunks += len(chunks)

        print(f"  SUCCESS: Added {len(chunks)} chunks to database")

    print(f"\n{'='*80}")
    print("RAG CHUNKING COMPLETE")
    print(f"{'='*80}")
    print(f"Documents chunked: {len(large_docs)}")
    print(f"Total chunks created: {total_chunks}")
    print(f"Average chunks per document: {total_chunks/len(large_docs):.1f}")
    print(f"\nDatabase now optimized for RAG retrieval!")
    print(f"{'='*80}")


def main():
    """Main execution"""
    print("\n" + "="*80)
    print("RAG CHUNKING SYSTEM")
    print("="*80)
    print("\nThis script optimizes large research papers for RAG retrieval by:")
    print("  1. Finding documents > 50K words (exceed LLM context limits)")
    print("  2. Splitting them into 2K-word chunks with 200-word overlap")
    print("  3. Maintaining all metadata and access status")
    print("  4. Enabling semantic search on manageable chunks")
    print()
    print("Papers with 700K+ words will be split into ~350 searchable chunks.")
    print("="*80)

    # Initialize ChromaDB
    print("\nConnecting to ChromaDB...")
    db_manager = ChromaDBManager(
        persist_directory="./chroma_db",
        collection_name="faculty_pulse"
    )

    print(f"Connected to collection: {db_manager.collection_name}")
    print(f"Current document count: {db_manager.get_collection_count()}")

    # Run chunking
    chunk_large_documents(
        db_manager=db_manager,
        threshold_words=50000,  # Chunk papers > 50K words
        chunk_size=2000,        # 2K words per chunk (safe for context)
        overlap=200             # 200 word overlap for continuity
    )

    # Final stats
    print(f"\nFinal database count: {db_manager.get_collection_count()}")
    print("\n✓ RAG system ready!")
    print("\nYour chatbot can now:")
    print("  - Handle papers of any size (even 700K+ words)")
    print("  - Retrieve only relevant sections")
    print("  - Stay within context limits")
    print("  - Provide accurate citations to specific chunks")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
