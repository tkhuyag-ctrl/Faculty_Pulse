"""
Test retrieval of Laura Been's publications from the database
Shows what the chatbot would receive when querying about Laura Been
"""
import sys
from chroma_manager import ChromaDBManager

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

def test_query(query_text):
    """Test a query and display results"""
    print(f"\n{'='*80}")
    print(f"QUERY: {query_text}")
    print(f"{'='*80}\n")

    manager = ChromaDBManager()
    results = manager.query_submissions(query_text, n_results=3)

    if not results or not results.get('documents'):
        print("❌ No results found!")
        return

    documents = results['documents'][0]
    distances = results.get('distances', [[]])[0]
    metadatas = results.get('metadatas', [[]])[0]

    print(f"✓ Found {len(documents)} results\n")

    for i, (doc, distance, metadata) in enumerate(zip(documents, distances, metadatas), 1):
        relevance = 1 - distance  # Convert distance to similarity score

        print(f"Result #{i}:")
        print(f"  Relevance Score: {relevance:.4f}")
        print(f"  Faculty: {metadata.get('faculty_name', 'Unknown')}")
        print(f"  Department: {metadata.get('department', 'Unknown')}")
        print(f"  Type: {metadata.get('content_type', 'Unknown')}")
        print(f"  Date: {metadata.get('date_published', 'Unknown')}")
        print(f"  Document Length: {len(doc)} characters")

        # Show preview of document
        preview = doc[:500] if len(doc) > 500 else doc
        print(f"\n  Document Preview:")
        print(f"  {'-'*76}")
        for line in preview.split('\n')[:10]:
            print(f"  {line}")
        if len(doc) > 500:
            print(f"  ... (truncated, full length: {len(doc)} chars)")
        print(f"  {'-'*76}\n")


def main():
    print("\n" + "="*80)
    print("LAURA BEEN PUBLICATION RETRIEVAL TEST")
    print("="*80)
    print("\nTesting various queries about Laura Been's research")
    print("This shows what context the chatbot would receive\n")

    # Test multiple queries
    queries = [
        "Laura Been tamoxifen research",
        "What has Laura Been published about brain-derived neurotrophic factor?",
        "Laura Been estrogen withdrawal studies",
        "Laura Been Psychology publications"
    ]

    for query in queries:
        test_query(query)
        print("\n" + "="*80)

    print("\n✓ Test complete!")
    print("\nNote: The chatbot would receive the top results and use them to")
    print("generate a natural language response using Claude API.\n")


if __name__ == "__main__":
    main()
