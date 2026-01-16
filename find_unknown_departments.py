"""
Find faculty with unknown departments
"""
import sys
from chroma_manager import ChromaDBManager

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

def main():
    print("\n" + "="*80)
    print("FACULTY WITH UNKNOWN DEPARTMENTS")
    print("="*80 + "\n")

    manager = ChromaDBManager()
    results = manager.collection.get(
        include=['metadatas'],
        where={'department': 'Unknown'}
    )

    # Get unique faculty names
    faculty_names = set(meta['faculty_name'] for meta in results['metadatas'])

    print(f"Total faculty with 'Unknown' department: {len(faculty_names)}")
    print(f"Total publications: {len(results['metadatas'])}\n")

    print("Faculty List:")
    for name in sorted(faculty_names):
        # Count publications for this faculty
        count = sum(1 for meta in results['metadatas'] if meta['faculty_name'] == name)
        print(f"  - {name} ({count} publications)")

    print("\n" + "="*80)

if __name__ == "__main__":
    main()
