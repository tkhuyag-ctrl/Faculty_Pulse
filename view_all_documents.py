"""
View All Documents in ChromaDB Database
Displays every single document with full details
"""
import sys
from chroma_manager import ChromaDBManager

# Fix encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

def view_all_documents():
    """Display all documents in the database"""
    print("\n" + "="*80)
    print("ALL DOCUMENTS IN FACULTY PULSE DATABASE")
    print("="*80 + "\n")

    # Initialize manager
    manager = ChromaDBManager(persist_directory="./chroma_db")

    # Get all submissions
    results = manager.get_all_submissions()
    total_count = len(results['ids'])

    if total_count == 0:
        print("Database is empty. No documents found.")
        return

    print(f"Total Documents: {total_count}\n")
    print("="*80 + "\n")

    # Display each document
    for i, (doc_id, doc, metadata) in enumerate(zip(
        results['ids'],
        results['documents'],
        results['metadatas']
    ), 1):
        print(f"{'#'*80}")
        print(f"DOCUMENT {i} of {total_count}")
        print(f"{'#'*80}\n")

        print(f"ID: {doc_id}")
        print(f"Faculty Name: {metadata['faculty_name']}")
        print(f"Department: {metadata['department']}")
        print(f"Content Type: {metadata['content_type']}")
        print(f"Date Published: {metadata['date_published']}")
        print(f"Document Length: {len(doc)} characters")
        print(f"\n{'-'*80}")
        print("DOCUMENT CONTENT:")
        print(f"{'-'*80}\n")
        print(doc)
        print(f"\n{'='*80}\n\n")

    print(f"\n{'#'*80}")
    print(f"END OF DATABASE - Total: {total_count} documents")
    print(f"{'#'*80}\n")


if __name__ == "__main__":
    view_all_documents()
