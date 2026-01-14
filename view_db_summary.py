"""
View summary of the ChromaDB database
"""
from chroma_manager import ChromaDBManager

if __name__ == "__main__":
    # Initialize the manager
    manager = ChromaDBManager()

    # Get all submissions
    results = manager.get_all_submissions()

    count = len(results['ids'])
    print(f"\n{'='*80}")
    print(f"DATABASE SUMMARY")
    print(f"{'='*80}")
    print(f"\nTotal submissions: {count}\n")

    if count == 0:
        print("Database is empty. No submissions found.")
    else:
        print(f"{'='*80}")
        print("SUBMISSION DETAILS")
        print(f"{'='*80}\n")

        for i, (doc_id, doc, metadata) in enumerate(zip(
            results['ids'],
            results['documents'],
            results['metadatas']
        ), 1):
            print(f"{i}. ID: {doc_id}")
            print(f"   Faculty: {metadata['faculty_name']}")
            print(f"   Department: {metadata['department']}")
            print(f"   Type: {metadata['content_type']}")
            print(f"   Date: {metadata['date_published']}")

            # Show first 200 characters of document
            doc_preview = doc[:200] + "..." if len(doc) > 200 else doc
            print(f"   Document (preview): {doc_preview}")
            print(f"   Document length: {len(doc)} characters")
            print(f"   {'-'*76}\n")
