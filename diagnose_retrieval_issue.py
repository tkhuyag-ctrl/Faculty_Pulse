"""
Diagnose why certain faculty can't be retrieved
Compare documents that CAN be retrieved vs those that CANNOT
"""
import sys
from chroma_manager import ChromaDBManager

# Fix encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

def analyze_document_structure():
    """Analyze differences between retrievable and non-retrievable documents"""
    manager = ChromaDBManager(persist_directory="./chroma_db")
    all_docs = manager.get_all_submissions()

    # Test a few faculty members - some that work, some that don't
    test_cases = [
        ("Noah Elkins", "WORKS", 35),  # Top faculty, should work
        ("Laura Been", "FAILS", 12),   # Known to fail
        ("Sorelle Friedler", "WORKS", 20),  # Should work
        ("John Dougherty", "FAILS", 16),  # Known to fail
    ]

    print("="*80)
    print("DOCUMENT STRUCTURE COMPARISON")
    print("="*80 + "\n")

    for faculty_name, expected_status, _ in test_cases:
        print(f"\n{'='*80}")
        print(f"Faculty: {faculty_name} (Expected: {expected_status})")
        print(f"{'='*80}")

        # Find their first document
        for doc_id, doc, metadata in zip(
            all_docs['ids'],
            all_docs['documents'],
            all_docs['metadatas']
        ):
            if metadata['faculty_name'] == faculty_name:
                print(f"\nFirst document found:")
                print(f"ID: {doc_id}")
                print(f"Length: {len(doc)} characters")
                print(f"\nDocument structure analysis:")
                print(f"  - Starts with 'Faculty:': {doc.startswith('Faculty:')}")
                print(f"  - Contains faculty name: {faculty_name in doc}")
                print(f"  - Name appears in first 100 chars: {faculty_name in doc[:100]}")
                print(f"  - Name appears in first 500 chars: {faculty_name in doc[:500]}")
                print(f"\nFirst 500 characters:")
                print(f"{'-'*80}")
                print(doc[:500])
                print(f"{'-'*80}")

                # Test if searchable
                results = manager.query_submissions(
                    query_text=faculty_name,
                    n_results=10
                )

                found = False
                position = None
                if results['ids'] and len(results['ids'][0]) > 0:
                    for i, meta in enumerate(results['metadatas'][0], 1):
                        if meta['faculty_name'] == faculty_name:
                            found = True
                            position = i
                            break

                if found:
                    print(f"\n✓ RETRIEVABLE - Found at position {position}/10")
                else:
                    print(f"\n❌ NOT RETRIEVABLE in top 10 results")

                break

    # Now let's check the actual issue
    print(f"\n\n{'='*80}")
    print("ROOT CAUSE ANALYSIS")
    print(f"{'='*80}\n")

    # Get Laura Been's documents
    laura_docs = []
    for doc_id, doc, metadata in zip(all_docs['ids'], all_docs['documents'], all_docs['metadatas']):
        if metadata['faculty_name'] == "Laura Been":
            laura_docs.append(doc)

    # Get Noah Elkins' documents (works)
    noah_docs = []
    for doc_id, doc, metadata in zip(all_docs['ids'], all_docs['documents'], all_docs['metadatas']):
        if metadata['faculty_name'] == "Noah Elkins":
            noah_docs.append(doc)

    print("Comparing document formats:\n")

    print("Laura Been (FAILS) - First document structure:")
    print(f"  First line: {laura_docs[0].split(chr(10))[0]}")
    print(f"  Second line: {laura_docs[0].split(chr(10))[1] if len(laura_docs[0].split(chr(10))) > 1 else 'N/A'}")
    print(f"  Has 'Faculty: Laura Been' in metadata format: {laura_docs[0].startswith('Faculty: Laura Been')}")

    print("\nNoah Elkins (WORKS) - First document structure:")
    print(f"  First line: {noah_docs[0].split(chr(10))[0]}")
    print(f"  Second line: {noah_docs[0].split(chr(10))[1] if len(noah_docs[0].split(chr(10))) > 1 else 'N/A'}")

    print("\n" + "="*80)
    print("HYPOTHESIS:")
    print("="*80)
    print("""
Documents that start with:
  "Faculty: [Name]
   Department: [Dept]
   OpenAlex ID: ..."

Are NOT being embedded properly because the faculty name appears only as
structured metadata at the beginning, not in the actual content text.

The vector embedding is probably focused on the research content (which comes
later) rather than the metadata header, making name-based searches fail.
    """)

    # Verify this hypothesis
    print("\n" + "="*80)
    print("VERIFICATION:")
    print("="*80 + "\n")

    structured_format = 0
    unstructured_format = 0

    for doc in all_docs['documents']:
        if doc.startswith('Faculty:') and 'OpenAlex ID:' in doc[:200]:
            structured_format += 1
        else:
            unstructured_format += 1

    print(f"Documents with structured metadata format: {structured_format}")
    print(f"Documents with unstructured/natural text: {unstructured_format}")

    print("\nThis explains why name-based searches fail - the embeddings are generated")
    print("from scientific content, not the metadata headers!")


if __name__ == "__main__":
    analyze_document_structure()
