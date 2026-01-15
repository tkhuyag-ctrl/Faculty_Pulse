"""
Deeper analysis - why does Noah Elkins work but Laura Been doesn't?
Both have the same document structure
"""
import sys
from chroma_manager import ChromaDBManager

# Fix encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

def deep_comparison():
    """Compare the actual content differences"""
    manager = ChromaDBManager(persist_directory="./chroma_db")
    all_docs = manager.get_all_submissions()

    print("="*80)
    print("DEEP COMPARISON: Why does Noah work but Laura doesn't?")
    print("="*80 + "\n")

    # Get both faculty's documents
    noah_doc = None
    laura_doc = None

    for doc_id, doc, metadata in zip(all_docs['ids'], all_docs['documents'], all_docs['metadatas']):
        if metadata['faculty_name'] == "Noah Elkins" and noah_doc is None:
            noah_doc = doc
        if metadata['faculty_name'] == "Laura Been" and laura_doc is None:
            laura_doc = doc

    print("NOAH ELKINS (WORKS):")
    print("="*80)
    print(f"Document length: {len(noah_doc)}")
    print(f"First 1000 characters:")
    print(noah_doc[:1000])
    print("\n" + "="*80 + "\n")

    print("LAURA BEEN (FAILS):")
    print("="*80)
    print(f"Document length: {len(laura_doc)}")
    print(f"First 1000 characters:")
    print(laura_doc[:1000])
    print("\n" + "="*80 + "\n")

    # Key insight: Check what comes AFTER the metadata
    print("CONTENT AFTER METADATA:")
    print("="*80)

    # Noah's content after metadata
    noah_lines = noah_doc.split('\n')
    print("\nNoah Elkins - Lines after metadata:")
    for i, line in enumerate(noah_lines[10:20], 10):  # Lines 10-20
        print(f"  {i}: {line[:100]}")

    # Laura's content after metadata
    laura_lines = laura_doc.split('\n')
    print("\nLaura Been - Lines after metadata:")
    for i, line in enumerate(laura_lines[10:20], 10):  # Lines 10-20
        print(f"  {i}: {line[:100]}")

    # Now the critical test: what does the embedding model "see"?
    print("\n" + "="*80)
    print("CRITICAL INSIGHT:")
    print("="*80)

    # Check if the name appears in the actual paper content
    noah_paper_start = noah_doc.find("FULL PAPER TEXT:")
    laura_paper_start = laura_doc.find("===")  # Different separator

    if noah_paper_start > 0:
        noah_paper_content = noah_doc[noah_paper_start:noah_paper_start+2000]
        print(f"\nNoah's paper content (first 500 chars after separator):")
        print(noah_paper_content[:500])
        print(f"\n'Noah Elkins' in paper content: {'Noah Elkins' in noah_paper_content}")

    if laura_paper_start > 0:
        laura_paper_content = laura_doc[laura_paper_start:laura_paper_start+2000]
        print(f"\nLaura's paper content (first 500 chars after separator):")
        print(laura_paper_content[:500])
        print(f"\n'Laura Been' in paper content: {'Laura Been' in laura_paper_content}")

    # The real test: content density
    print("\n" + "="*80)
    print("CONTENT DENSITY TEST:")
    print("="*80)

    # How many times does each name appear in their document?
    noah_count = noah_doc.count("Noah Elkins") + noah_doc.count("Elkins")
    laura_count = laura_doc.count("Laura Been") + laura_doc.count("Been")

    print(f"\n'Noah Elkins' / 'Elkins' appears: {noah_count} times")
    print(f"'Laura Been' / 'Been' appears: {laura_count} times")

    # Check the paper content specifically
    if noah_paper_start > 0:
        noah_paper_full = noah_doc[noah_paper_start:]
        print(f"\nIn Noah's paper content: {noah_paper_full.count('Elkins')} times")

    if laura_paper_start > 0:
        laura_paper_full = laura_doc[laura_paper_start:]
        # Note: "Been" is a common English word, might appear in different context
        print(f"In Laura's paper content: {laura_paper_full.count('Been')} times")
        print(f"In Laura's paper content (full name): {laura_paper_full.count('Laura Been')} times")


def test_name_ambiguity():
    """Test if 'Been' is too ambiguous as a search term"""
    print("\n" + "="*80)
    print("NAME AMBIGUITY TEST:")
    print("="*80)

    manager = ChromaDBManager(persist_directory="./chroma_db")

    # Test different name formats
    test_queries = [
        ("Laura Been", "Full name"),
        ("Been", "Last name only"),
        ("Laura", "First name only"),
        ("Laura Been Psychology", "Name + Department"),
        ("Laura Been estrogen", "Name + Research topic"),
    ]

    for query, description in test_queries:
        print(f"\n🔍 Query: '{query}' ({description})")
        print("-"*80)

        results = manager.query_submissions(query_text=query, n_results=5)

        if results['ids'] and len(results['ids'][0]) > 0:
            for i, (metadata, distance) in enumerate(zip(
                results['metadatas'][0],
                results['distances'][0]
            ), 1):
                marker = "✓" if metadata['faculty_name'] == "Laura Been" else ""
                print(f"  {i}. {metadata['faculty_name']} (dist: {distance:.3f}) {marker}")


if __name__ == "__main__":
    deep_comparison()
    test_name_ambiguity()
