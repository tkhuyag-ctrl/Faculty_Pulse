"""
Inspect ChromaDB Database Contents
Shows all documents, metadata, and statistics in the Faculty Pulse database
"""
import sys
from chroma_manager import ChromaDBManager
from collections import Counter

# Fix encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

def inspect_database():
    """Inspect and display database contents with statistics"""
    print("\n" + "="*80)
    print("FACULTY PULSE DATABASE INSPECTOR")
    print("="*80 + "\n")

    # Initialize manager
    manager = ChromaDBManager(persist_directory="./chroma_db")

    # Get all submissions
    results = manager.get_all_submissions()
    total_count = len(results['ids'])

    if total_count == 0:
        print("❌ Database is empty. No documents found.")
        return

    print(f"✓ Total Documents: {total_count}\n")

    # Gather statistics
    content_types = Counter()
    departments = Counter()
    faculty_names = Counter()
    dates = []

    for metadata in results['metadatas']:
        content_types[metadata['content_type']] += 1
        departments[metadata['department']] += 1
        faculty_names[metadata['faculty_name']] += 1
        dates.append(metadata['date_published'])

    # Display statistics
    print("="*80)
    print("DATABASE STATISTICS")
    print("="*80 + "\n")

    print(f"📊 Content Types:")
    for content_type, count in content_types.most_common():
        percentage = (count / total_count) * 100
        print(f"   • {content_type}: {count} ({percentage:.1f}%)")

    print(f"\n🏛️  Departments ({len(departments)} total):")
    for dept, count in sorted(departments.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"   • {dept}: {count}")
    if len(departments) > 10:
        print(f"   ... and {len(departments) - 10} more")

    print(f"\n👤 Top Faculty Members by Document Count:")
    for name, count in faculty_names.most_common(10):
        print(f"   • {name}: {count}")

    # Display sample documents
    print("\n" + "="*80)
    print("SAMPLE DOCUMENTS (First 10)")
    print("="*80 + "\n")

    for i, (doc_id, doc, metadata) in enumerate(zip(
        results['ids'][:10],
        results['documents'][:10],
        results['metadatas'][:10]
    ), 1):
        print(f"{i}. ID: {doc_id}")
        print(f"   Faculty: {metadata['faculty_name']}")
        print(f"   Department: {metadata['department']}")
        print(f"   Type: {metadata['content_type']}")
        print(f"   Date: {metadata['date_published']}")

        # Show document preview
        doc_preview = doc[:300] if len(doc) > 300 else doc
        print(f"   Document: {doc_preview}{'...' if len(doc) > 300 else ''}")
        print(f"   Document Length: {len(doc)} characters")
        print(f"   {'-'*76}\n")

    if total_count > 10:
        print(f"... and {total_count - 10} more documents\n")

    # Option to display all
    print("="*80)
    print("To see ALL documents, uncomment the line below:")
    print("# manager.display_all_submissions()")
    print("="*80 + "\n")


if __name__ == "__main__":
    inspect_database()
