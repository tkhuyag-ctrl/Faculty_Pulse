"""
Test document retrieval for specific faculty members
Debug why certain faculty can't be retrieved
"""
import sys
from chroma_manager import ChromaDBManager

# Fix encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

def test_faculty_retrieval(faculty_name):
    """Test retrieval for a specific faculty member"""
    print(f"\n{'='*80}")
    print(f"TESTING RETRIEVAL FOR: {faculty_name}")
    print(f"{'='*80}\n")

    manager = ChromaDBManager(persist_directory="./chroma_db")

    # First, find all documents for this faculty in the database
    all_docs = manager.get_all_submissions()
    faculty_docs = []

    for i, (doc_id, doc, metadata) in enumerate(zip(
        all_docs['ids'],
        all_docs['documents'],
        all_docs['metadatas']
    )):
        if metadata['faculty_name'] == faculty_name:
            faculty_docs.append({
                'id': doc_id,
                'document': doc,
                'metadata': metadata,
                'doc_length': len(doc)
            })

    print(f"📊 DOCUMENTS IN DATABASE FOR {faculty_name}: {len(faculty_docs)}")

    if len(faculty_docs) == 0:
        print(f"❌ No documents found for {faculty_name}")
        return

    # Show what's in the database
    print(f"\nDocuments stored:")
    for i, doc in enumerate(faculty_docs, 1):
        print(f"\n{i}. ID: {doc['id']}")
        print(f"   Department: {doc['metadata']['department']}")
        print(f"   Type: {doc['metadata']['content_type']}")
        print(f"   Date: {doc['metadata']['date_published']}")
        print(f"   Length: {doc['doc_length']} characters")
        print(f"   Content preview: {doc['document'][:200]}...")

    # Now test different query variations
    print(f"\n{'='*80}")
    print(f"TESTING DIFFERENT QUERIES")
    print(f"{'='*80}\n")

    test_queries = [
        f"{faculty_name}",
        f"publications by {faculty_name}",
        f"research by {faculty_name}",
        f"What has {faculty_name} published?",
        f"{faculty_name.split()[-1]}",  # Last name only
    ]

    for query in test_queries:
        print(f"\n🔍 Query: '{query}'")
        print(f"{'-'*80}")

        results = manager.query_submissions(
            query_text=query,
            n_results=5
        )

        num_results = len(results['ids'][0]) if results['ids'] else 0
        print(f"Results returned: {num_results}")

        if num_results > 0:
            # Check if any results are for our target faculty
            found_target = False
            for j, (doc_id, metadata, distance) in enumerate(zip(
                results['ids'][0],
                results['metadatas'][0],
                results['distances'][0]
            ), 1):
                is_target = metadata['faculty_name'] == faculty_name
                marker = "✓ TARGET" if is_target else ""
                if is_target:
                    found_target = True

                print(f"  {j}. Faculty: {metadata['faculty_name']} {marker}")
                print(f"     Distance: {distance:.4f} (Relevance: {1-distance:.4f})")
                print(f"     Department: {metadata['department']}")

            if found_target:
                print(f"  ✓ Successfully retrieved {faculty_name}")
            else:
                print(f"  ❌ {faculty_name} NOT in top 5 results")
        else:
            print(f"  ❌ No results returned")


def find_problematic_faculty():
    """Find all faculty members with retrieval issues"""
    print(f"\n{'='*80}")
    print(f"ANALYZING ALL FACULTY FOR RETRIEVAL ISSUES")
    print(f"{'='*80}\n")

    manager = ChromaDBManager(persist_directory="./chroma_db")
    all_docs = manager.get_all_submissions()

    # Get unique faculty members
    faculty_dict = {}
    for metadata in all_docs['metadatas']:
        name = metadata['faculty_name']
        if name not in faculty_dict:
            faculty_dict[name] = {
                'count': 0,
                'departments': set(),
                'content_types': set()
            }
        faculty_dict[name]['count'] += 1
        faculty_dict[name]['departments'].add(metadata['department'])
        faculty_dict[name]['content_types'].add(metadata['content_type'])

    print(f"Total unique faculty: {len(faculty_dict)}")
    print(f"\nTesting retrieval for each faculty member...\n")

    problematic = []

    for faculty_name in sorted(faculty_dict.keys()):
        # Test if we can retrieve this faculty member
        results = manager.query_submissions(
            query_text=faculty_name,
            n_results=5
        )

        # Check if faculty appears in top 5 results
        found = False
        if results['ids'] and len(results['ids'][0]) > 0:
            for metadata in results['metadatas'][0]:
                if metadata['faculty_name'] == faculty_name:
                    found = True
                    break

        status = "✓" if found else "❌"
        doc_count = faculty_dict[faculty_name]['count']

        if not found:
            problematic.append((faculty_name, doc_count))
            print(f"{status} {faculty_name} ({doc_count} docs) - CANNOT RETRIEVE")

    # Summary
    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}\n")
    print(f"Total faculty: {len(faculty_dict)}")
    print(f"Problematic retrievals: {len(problematic)}")

    if problematic:
        print(f"\n❌ Faculty members that CANNOT be retrieved:")
        for name, count in sorted(problematic, key=lambda x: x[1], reverse=True):
            print(f"   • {name} ({count} documents)")

    return problematic


if __name__ == "__main__":
    # Test Laura Been specifically
    test_faculty_retrieval("Laura Been")

    # Find all problematic faculty
    print("\n\n")
    problematic = find_problematic_faculty()
