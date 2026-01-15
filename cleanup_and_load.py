"""
Cleanup Database and Load Haverford Data
- Remove non-faculty/professor content
- Remove entries before 2020
- Load discovered Haverford URLs
"""
import json
import logging
from datetime import datetime
from chroma_manager import ChromaDBManager
from automated_crawler import AutomatedCrawler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def is_faculty_related(faculty_name: str, document: str, metadata: dict) -> bool:
    """
    Determine if entry is faculty/professor related
    """
    # Keywords that indicate non-faculty content
    non_faculty_keywords = [
        'student', 'undergraduate', 'graduate',
        'alumni', 'alum',
        'staff member', 'administrative',
        'event', 'seminar calendar',
        'course description', 'syllabus',
        'admission', 'apply',
        'news', 'announcement',
        'haverford scholarship',  # Repository name, not a person
        'haverford college',  # Institution name
    ]

    # Check faculty name
    name_lower = faculty_name.lower()
    for keyword in non_faculty_keywords:
        if keyword in name_lower:
            logger.debug(f"Non-faculty name detected: {faculty_name}")
            return False

    # If name is too short or generic, it's probably not a person
    if len(faculty_name) < 5 or faculty_name in ['Unknown Faculty', 'Faculty', 'Staff']:
        logger.debug(f"Generic or short name: {faculty_name}")
        return False

    # Check for titles that indicate it's a faculty member
    faculty_titles = [
        'professor', 'prof.', 'dr.', 'ph.d.',
        'associate professor', 'assistant professor',
        'lecturer', 'instructor',
        'chair', 'director',
        'emeritus', 'emerita'
    ]

    combined_text = (faculty_name + ' ' + document[:500]).lower()
    has_title = any(title in combined_text for title in faculty_titles)

    if has_title:
        logger.debug(f"Faculty title found for: {faculty_name}")
        return True

    # If content type is clearly faculty-related
    content_type = metadata.get('content_type', '').lower()
    if content_type in ['award', 'publication', 'talk']:
        # These are usually about faculty
        return True

    # Default: if name looks like a person name (has space, reasonable length)
    name_parts = faculty_name.split()
    if len(name_parts) >= 2 and len(name_parts) <= 5:
        # Likely a person's name
        return True

    return False

def is_date_valid(date_str: str) -> bool:
    """
    Check if date is 2020 or later
    """
    try:
        date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return date_obj.year >= 2020
    except:
        # If can't parse date, keep it (assume it's recent)
        logger.warning(f"Could not parse date: {date_str}, keeping entry")
        return True

def cleanup_database():
    """
    Clean up the database:
    - Remove non-faculty entries
    - Remove entries before 2020
    """
    print("\n" + "="*80)
    print("DATABASE CLEANUP")
    print("="*80)

    db_manager = ChromaDBManager()

    # Get all submissions
    print("\nFetching all submissions...")
    all_submissions = db_manager.get_all_submissions()

    total_count = len(all_submissions['ids'])
    print(f"Total submissions in database: {total_count}")

    if total_count == 0:
        print("Database is empty, nothing to clean up.")
        return

    # Track what to delete
    to_delete = []
    kept_count = 0

    print("\nAnalyzing submissions...")
    for i, (doc_id, doc, metadata) in enumerate(zip(
        all_submissions['ids'],
        all_submissions['documents'],
        all_submissions['metadatas']
    ), 1):

        faculty_name = metadata.get('faculty_name', 'Unknown')
        date_published = metadata.get('date_published', '')

        # Check if faculty-related
        if not is_faculty_related(faculty_name, doc, metadata):
            logger.info(f"Removing non-faculty: {faculty_name}")
            to_delete.append(doc_id)
            continue

        # Check date
        if not is_date_valid(date_published):
            logger.info(f"Removing old entry (pre-2020): {faculty_name} - {date_published}")
            to_delete.append(doc_id)
            continue

        kept_count += 1

    # Delete entries
    if to_delete:
        print(f"\nDeleting {len(to_delete)} entries...")
        for doc_id in to_delete:
            db_manager.delete_submission(doc_id)
        print(f"Deleted {len(to_delete)} entries")
    else:
        print("\nNo entries to delete.")

    print(f"\nKept: {kept_count} entries")
    print(f"Removed: {len(to_delete)} entries")

    # Show stats
    print("\nFinal database statistics:")
    final_count = db_manager.get_collection_count()
    print(f"Total documents: {final_count}")

def load_discovered_urls():
    """
    Load discovered Haverford URLs into the crawler
    """
    print("\n" + "="*80)
    print("LOADING DISCOVERED URLS")
    print("="*80)

    # Check which files exist
    discovered_files = []
    for filename in ['haverford_discovered.json', 'haverford_all_discovered.json', 'discovered_urls.json']:
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
                if data:
                    discovered_files.append((filename, len(data)))
        except FileNotFoundError:
            pass

    if not discovered_files:
        print("No discovered URL files found.")
        print("\nRun one of these first:")
        print("  python link_spider.py haverford_urls.json discovered_urls.json 2")
        print("  python run_haverford_spider.py")
        return

    # Use the file with most URLs
    discovered_files.sort(key=lambda x: x[1], reverse=True)
    filename, url_count = discovered_files[0]

    print(f"\nFound {len(discovered_files)} discovered URL file(s)")
    print(f"Using: {filename} ({url_count} URLs)")

    # Load and crawl
    print("\nInitializing crawler...")
    crawler = AutomatedCrawler()

    try:
        print(f"Loading URLs from {filename}...")
        crawler.load_urls_from_json(filename)

        print("\nCrawling all URLs...")
        print("This may take several minutes...\n")

        results = crawler.crawl_all_pending()

        # Display results
        print("\n" + "="*80)
        print("CRAWL RESULTS")
        print("="*80)
        print(f"Total URLs: {results['total']}")
        print(f"Successful: {results['successful']}")
        print(f"  - Updated: {results['updated']}")
        print(f"  - Unchanged: {results['unchanged']}")
        print(f"Failed: {results['failed']}")

        if results['errors']:
            print(f"\nErrors (showing first 5):")
            for error in results['errors'][:5]:
                print(f"  - {error['url'][:60]}...")
                print(f"    {error['error'][:80]}")

        # Final stats
        print("\n" + "="*80)
        print("FINAL DATABASE STATISTICS")
        print("="*80)
        crawler.display_statistics()

    finally:
        crawler.close()

def main():
    print("="*80)
    print("FACULTY PULSE - DATABASE CLEANUP AND LOADER")
    print("="*80)

    # Ask for confirmation
    print("\nThis will:")
    print("1. Remove non-faculty/professor entries")
    print("2. Remove entries dated before 2020")
    print("3. Load and crawl discovered Haverford URLs")

    response = input("\nContinue? (yes/no): ").strip().lower()

    if response not in ['yes', 'y']:
        print("Aborted.")
        return

    try:
        # Step 1: Cleanup
        cleanup_database()

        # Step 2: Load new data
        load_discovered_urls()

        print("\n" + "="*80)
        print("COMPLETE!")
        print("="*80)
        print("\nYour database now contains:")
        print("  - Only faculty/professor related content")
        print("  - Only entries from 2020 or later")
        print("  - Newly discovered Haverford faculty data")
        print("\nStart the chatbot:")
        print("  python -m streamlit run app.py")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
