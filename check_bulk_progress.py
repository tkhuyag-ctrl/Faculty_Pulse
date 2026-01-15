"""
Check progress of bulk faculty processing
"""
import sys
from chroma_manager import ChromaDBManager

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

def main():
    print("\n" + "="*80)
    print("BULK PROCESSING PROGRESS")
    print("="*80 + "\n")

    try:
        manager = ChromaDBManager()
        count = manager.collection.count()

        print(f"✓ Documents in database: {count}")
        print()

        # Estimated progress (139 faculty, ~2780 publications expected)
        estimated_total = 2780
        progress_pct = (count / estimated_total * 100) if count > 0 else 0

        print(f"Estimated progress: {progress_pct:.1f}% of expected {estimated_total} publications")
        print()

        # Sample some recent additions
        if count > 0:
            results = manager.collection.get(limit=5, include=['metadatas'])
            print("Recent additions:")
            seen_faculty = set()
            for metadata in results['metadatas']:
                faculty = metadata.get('faculty_name', 'Unknown')
                dept = metadata.get('department', 'Unknown')
                if faculty not in seen_faculty:
                    print(f"  - {faculty} ({dept})")
                    seen_faculty.add(faculty)
            print()

        print("The bulk processing is running in the background.")
        print("Check again in 10-15 minutes to see progress.")
        print()
        print("To see live output:")
        print("  tail -f bulk_faculty_fetch_*.log")
        print()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
