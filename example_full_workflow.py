"""
Complete Workflow Example: URLs -> Text Extraction -> ChromaDB
This script demonstrates the full workflow from web URLs to ChromaDB storage
"""
from data_extractor import DataExtractor
from chroma_manager import ChromaDBManager
import json


def full_workflow_example():
    """
    Demonstrate complete workflow:
    1. Extract text from URLs in JSON file
    2. Add extracted entries to ChromaDB
    3. Query the database
    """
    print("=" * 80)
    print("FULL WORKFLOW EXAMPLE: URLs -> Text Extraction -> ChromaDB")
    print("=" * 80)

    # Step 1: Extract text from URLs
    print("\n[STEP 1] Extracting text from web URLs...")
    print("-" * 80)

    extractor = DataExtractor(delay=2.0, max_retries=3)
    input_file = "input_data.json"
    output_dir = "data"

    try:
        extractor.process_json_file(input_file, output_dir)
    except Exception as e:
        print(f"Error during extraction: {e}")
        return

    # Step 2: Load extracted entries from data directory
    print("\n[STEP 2] Loading extracted entries from data directory...")
    print("-" * 80)

    import os
    entries = []
    if os.path.exists(output_dir):
        for filename in os.listdir(output_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(output_dir, filename)
                with open(filepath, 'r') as f:
                    entry = json.load(f)
                    entries.append(entry)

    print(f"Loaded {len(entries)} extracted entries from {output_dir}/")

    # Step 3: Initialize ChromaDB and clear previous data
    print("\n[STEP 3] Initializing ChromaDB...")
    print("-" * 80)

    manager = ChromaDBManager()

    # Optional: Clear database for fresh start
    if manager.get_collection_count() > 0:
        print("Clearing existing database for clean demo...")
        manager.clear_database()

    # Step 4: Add entries to ChromaDB
    print("\n[STEP 4] Adding entries to ChromaDB...")
    print("-" * 80)

    for entry in entries:
        print(f"\nAdding entry: {entry['id']}")
        print(f"  Faculty: {entry['metadata']['faculty_name']}")
        print(f"  Document length: {len(entry['document'])} characters")

        manager.add_single_submission(
            document=entry['document'],
            faculty_name=entry['metadata']['faculty_name'],
            date_published=entry['metadata']['date_published'],
            content_type=entry['metadata']['content_type'],
            department=entry['metadata']['department'],
            submission_id=entry.get('id')
        )

    # Step 5: Verify data in ChromaDB
    print("\n[STEP 5] Verifying data in ChromaDB...")
    print("-" * 80)

    count = manager.get_collection_count()
    print(f"\nTotal entries in database: {count}")

    manager.display_all_submissions()

    # Step 6: Query the database
    print("\n[STEP 6] Querying the database...")
    print("-" * 80)

    query_text = "machine learning artificial intelligence"
    print(f"\nSearching for: '{query_text}'")

    results = manager.query_submissions(query_text, n_results=5)

    print(f"\nFound {len(results['ids'][0])} results:")
    for i, (doc_id, doc, metadata, distance) in enumerate(zip(
        results['ids'][0],
        results['documents'][0],
        results['metadatas'][0],
        results['distances'][0]
    ), 1):
        print(f"\n  {i}. ID: {doc_id}")
        print(f"     Faculty: {metadata['faculty_name']}")
        print(f"     Department: {metadata['department']}")
        print(f"     Similarity Score: {1 - distance:.4f}")
        print(f"     Document Preview: {doc[:150]}...")

    print("\n" + "=" * 80)
    print("WORKFLOW COMPLETE!")
    print("=" * 80)


if __name__ == "__main__":
    full_workflow_example()
