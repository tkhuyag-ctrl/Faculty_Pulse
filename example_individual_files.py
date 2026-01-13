"""
Example: Extract URLs and save as individual files, then load into ChromaDB
"""
from data_extractor import DataExtractor
from chroma_manager import ChromaDBManager
import json
import os


def load_entries_from_directory(directory: str):
    """
    Load all JSON entries from a directory

    Args:
        directory: Path to directory containing JSON files

    Returns:
        List of entry dictionaries
    """
    entries = []
    if os.path.exists(directory):
        for filename in sorted(os.listdir(directory)):
            if filename.endswith('.json'):
                filepath = os.path.join(directory, filename)
                with open(filepath, 'r') as f:
                    entry = json.load(f)
                    entries.append(entry)
    return entries


def main():
    print("=" * 80)
    print("EXAMPLE: Individual File Extraction -> ChromaDB")
    print("=" * 80)

    # Step 1: Extract text from URLs and save as individual files
    print("\n[STEP 1] Extracting text and saving individual files...")
    print("-" * 80)

    extractor = DataExtractor(delay=1.0)
    input_file = "data_example_multiple_urls.json"
    output_dir = "data"

    extractor.process_json_file(input_file, output_dir)

    # Step 2: Load entries from data directory
    print("\n[STEP 2] Loading entries from data directory...")
    print("-" * 80)

    entries = load_entries_from_directory(output_dir)
    print(f"Loaded {len(entries)} entries from {output_dir}/")

    for entry in entries:
        print(f"  - {entry['id']}: {len(entry['document'])} characters")

    # Step 3: Initialize ChromaDB
    print("\n[STEP 3] Adding entries to ChromaDB...")
    print("-" * 80)

    manager = ChromaDBManager()

    for entry in entries:
        print(f"\nAdding {entry['id']}...")
        manager.add_single_submission(
            document=entry['document'],
            faculty_name=entry['metadata']['faculty_name'],
            date_published=entry['metadata']['date_published'],
            content_type=entry['metadata']['content_type'],
            department=entry['metadata']['department'],
            submission_id=entry.get('id')
        )

    # Step 4: Query the database
    print("\n[STEP 4] Querying the database...")
    print("-" * 80)

    results = manager.query_submissions("machine learning", n_results=3)
    print(f"\nFound {len(results['ids'][0])} results for 'machine learning':")

    for i, (doc_id, metadata) in enumerate(zip(results['ids'][0], results['metadatas'][0]), 1):
        print(f"  {i}. {doc_id} - {metadata['faculty_name']}")

    print("\n" + "=" * 80)
    print("COMPLETE!")
    print("=" * 80)


if __name__ == "__main__":
    main()
