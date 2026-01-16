"""
Diagnose search quality issues in ChromaDB
"""
import os
from dotenv import load_dotenv
from chroma_manager import ChromaDBManager
from chatbot import FacultyPulseChatbot

load_dotenv()

def test_search_quality():
    """Test search quality with various queries"""

    chroma = ChromaDBManager()

    print("="*80)
    print("CHROMADB SEARCH QUALITY DIAGNOSTICS")
    print("="*80)
    print(f"\nTotal documents: {chroma.collection.count()}")

    # Get sample documents
    sample = chroma.collection.get(limit=5)
    print(f"\nSample documents in DB:")
    for i, (doc, meta) in enumerate(zip(sample['documents'], sample['metadatas']), 1):
        print(f"\n{i}. Faculty: {meta.get('faculty_name', 'N/A')}")
        print(f"   Type: {meta.get('content_type', 'N/A')}")
        print(f"   Date: {meta.get('date_published', 'N/A')}")
        print(f"   Title: {meta.get('title', 'N/A')[:100]}")

    print("\n" + "="*80)
    print("TESTING SEARCH QUERIES")
    print("="*80)

    test_queries = [
        "machine learning publications",
        "computer science research",
        "awards received by faculty",
        "publications from 2025",
        "recent publications"
    ]

    for query in test_queries:
        print(f"\n\nQuery: '{query}'")
        print("-" * 60)

        # Test raw ChromaDB query
        results = chroma.query_submissions(query, n_results=5)

        if results and 'distances' in results and results['distances']:
            distances = results['distances'][0]
            metadatas = results['metadatas'][0]

            print(f"Found {len(distances)} results:")
            for i, (dist, meta) in enumerate(zip(distances, metadatas), 1):
                relevance = 1 - dist  # Convert distance to relevance
                print(f"\n  {i}. Relevance: {relevance:.3f} (distance: {dist:.3f})")
                print(f"     Faculty: {meta.get('faculty_name', 'N/A')}")
                print(f"     Type: {meta.get('content_type', 'N/A')}")
                print(f"     Date: {meta.get('date_published', 'N/A')}")
                print(f"     Title: {meta.get('title', 'N/A')[:80]}...")
        else:
            print("  No results found!")

    print("\n" + "="*80)
    print("EMBEDDING MODEL INFO")
    print("="*80)
    print("ChromaDB is using the DEFAULT embedding model")
    print("Default: sentence-transformers/all-MiniLM-L6-v2")
    print("  - Very small model (22M parameters)")
    print("  - Fast but lower quality embeddings")
    print("  - Dimension: 384")
    print("\nBETTER OPTIONS:")
    print("  1. all-mpnet-base-v2 (110M params, dim 768) - Best quality")
    print("  2. all-MiniLM-L12-v2 (33M params, dim 384) - Better than L6")
    print("  3. OpenAI text-embedding-3-small - Commercial, very good")

    # Check what embedding function is being used
    print(f"\nCurrent collection metadata: {chroma.collection.metadata}")

if __name__ == "__main__":
    test_search_quality()
