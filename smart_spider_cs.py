"""
Smart Spider for CS Faculty - Improved with validation
Only extracts valid faculty with proper names, departments, and recent publications (2020+)
"""
import re
import logging
from datetime import datetime
from typing import List, Dict, Optional
from link_spider import LinkSpider
from automated_crawler import AutomatedCrawler
from chroma_manager import ChromaDBManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('smart_spider_cs.log')
    ]
)

logger = logging.getLogger(__name__)


def is_valid_person_name(name: str) -> bool:
    """Check if name looks like a real person's name"""
    if not name or name == "Unknown Faculty":
        return False

    # Remove common non-person indicators
    non_person_keywords = [
        'scholarship', 'repository', 'college', 'university',
        'department', 'school', 'institute', 'center',
        'library', 'archive', 'collection', 'database',
        'haverford', 'welcome', 'home', 'about'
    ]

    name_lower = name.lower()

    # Check for non-person keywords
    for keyword in non_person_keywords:
        if keyword in name_lower:
            logger.debug(f"Rejected name (non-person keyword): {name}")
            return False

    # Name should have at least 2 parts (first and last name)
    name_parts = [p for p in name.split() if len(p) > 1]
    if len(name_parts) < 2 or len(name_parts) > 5:
        logger.debug(f"Rejected name (wrong part count): {name}")
        return False

    # Each part should be reasonable length (2-20 characters)
    for part in name_parts:
        # Remove titles
        if part.lower() in ['dr.', 'prof.', 'mr.', 'mrs.', 'ms.', 'ph.d.']:
            continue
        if len(part) < 2 or len(part) > 20:
            logger.debug(f"Rejected name (part too short/long): {name}")
            return False

    # Should not be all uppercase (usually indicates non-person)
    if name.isupper() and len(name) > 10:
        logger.debug(f"Rejected name (all caps): {name}")
        return False

    logger.debug(f"Accepted name: {name}")
    return True


def is_valid_department(department: str) -> bool:
    """Check if department is a valid academic department"""
    if not department or department == "Unknown Department":
        return False

    # List of valid academic departments
    valid_departments = [
        'computer science', 'cs',
        'biology', 'chemistry', 'physics', 'mathematics', 'math',
        'psychology', 'economics', 'philosophy', 'history',
        'english', 'literature', 'classics', 'linguistics',
        'political science', 'sociology', 'anthropology',
        'art', 'music', 'theater', 'dance',
        'astronomy', 'geology', 'environmental science',
        'education', 'religion', 'comparative literature'
    ]

    dept_lower = department.lower()

    # Check if it matches any valid department
    for valid_dept in valid_departments:
        if valid_dept in dept_lower or dept_lower in valid_dept:
            return True

    logger.debug(f"Rejected department: {department}")
    return False


def extract_year_from_content(content: str) -> Optional[int]:
    """Try to extract publication year from content"""
    # Look for year patterns (2020-2026)
    year_patterns = [
        r'\b(202[0-6])\b',  # Years 2020-2026
        r'Published[:\s]+(202[0-6])',
        r'Date[:\s]+(202[0-6])',
        r'\(202[0-6]\)',
    ]

    for pattern in year_patterns:
        match = re.search(pattern, content)
        if match:
            year = int(match.group(1))
            if 2020 <= year <= 2030:
                return year

    return None


def is_recent_publication(content: str, date_published: str) -> bool:
    """Check if publication is from 2020 or later"""
    # Try from date_published field
    try:
        date_obj = datetime.fromisoformat(date_published.replace('Z', '+00:00'))
        if date_obj.year >= 2020:
            return True
    except:
        pass

    # Try extracting from content
    year = extract_year_from_content(content)
    if year and year >= 2020:
        return True

    logger.debug(f"Rejected - publication too old or year unknown")
    return False


def run_smart_cs_spider():
    """Run spider on CS faculty page with smart filtering"""
    print("="*80)
    print("SMART CS FACULTY SPIDER")
    print("="*80)

    # CS Faculty URL
    cs_faculty_url = "https://www.haverford.edu/computer-science/faculty-staff"

    print(f"\nTarget: {cs_faculty_url}")
    print("Filters:")
    print("  - Only valid person names")
    print("  - Only valid academic departments")
    print("  - Only publications from 2020+")
    print()

    # Create spider with permissive patterns for CS
    spider = LinkSpider(
        seed_urls=[cs_faculty_url],
        max_depth=2,  # Go 2 levels deep
        max_urls_per_domain=100,
        allowed_patterns=[
            r'haverford\.edu/computer-science',  # CS department pages
            r'haverford\.edu/.*faculty',          # Faculty pages
            r'haverford\.edu/.*staff',            # Staff pages
            r'\.pdf$',                             # PDFs
        ],
        excluded_patterns=[
            r'/calendar', r'/events', r'/news', r'/apply',
            r'/admissions', r'/give', r'/login', r'/admin',
            r'#', r'\?share', r'\.jpg$', r'\.png$', r'\.css$', r'\.js$',
        ]
    )

    try:
        print("Step 1: Discovering URLs...")
        results = spider.crawl()

        print(f"\nDiscovered {len(results)} URLs")

        # Filter results
        print("\nStep 2: Filtering results...")
        valid_results = []

        for result in results:
            faculty_name = result['faculty_name']
            department = result['department']

            # Validate name
            if not is_valid_person_name(faculty_name):
                logger.info(f"Filtered out - invalid name: {faculty_name}")
                continue

            # Validate department
            if not is_valid_department(department):
                logger.info(f"Filtered out - invalid department: {department} (faculty: {faculty_name})")
                continue

            valid_results.append(result)
            print(f"  Valid: {faculty_name} - {department}")

        print(f"\nValid URLs: {len(valid_results)}/{len(results)}")

        if not valid_results:
            print("\nNo valid faculty URLs found.")
            print("This might mean:")
            print("  - The spider didn't find individual faculty pages")
            print("  - Department extraction needs refinement")
            return

        # Save valid results
        import json
        output_file = "cs_faculty_validated.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(valid_results, f, indent=2, ensure_ascii=False)

        print(f"\nSaved to: {output_file}")

        # Step 3: Crawl and load
        print("\n" + "="*80)
        print("Step 3: Crawling and loading into database...")
        print("="*80)

        crawler = AutomatedCrawler()

        # Load URLs
        print(f"\nLoading {len(valid_results)} URLs...")
        crawler.load_urls_from_json(output_file)

        # Crawl
        print("\nFetching content (this may take several minutes)...")
        crawl_results = crawler.crawl_all_pending()

        print(f"\nCrawl Results:")
        print(f"  Total: {crawl_results['total']}")
        print(f"  Successful: {crawl_results['successful']}")
        print(f"  Failed: {crawl_results['failed']}")

        # Step 4: Final validation - remove old publications from database
        print("\n" + "="*80)
        print("Step 4: Final cleanup (removing pre-2020 publications)...")
        print("="*80)

        db = ChromaDBManager()
        all_data = db.get_all_submissions()

        to_delete = []
        kept = 0

        for doc_id, doc, metadata in zip(
            all_data['ids'],
            all_data['documents'],
            all_data['metadatas']
        ):
            faculty_name = metadata.get('faculty_name', '')
            department = metadata.get('department', '')
            date_published = metadata.get('date_published', '')

            # Re-validate
            if not is_valid_person_name(faculty_name):
                logger.info(f"Removing (invalid name): {faculty_name}")
                to_delete.append(doc_id)
                continue

            if not is_valid_department(department):
                logger.info(f"Removing (invalid department): {department} - {faculty_name}")
                to_delete.append(doc_id)
                continue

            if not is_recent_publication(doc, date_published):
                logger.info(f"Removing (old publication): {faculty_name}")
                to_delete.append(doc_id)
                continue

            kept += 1

        # Delete invalid entries
        if to_delete:
            print(f"\nRemoving {len(to_delete)} invalid entries...")
            for doc_id in to_delete:
                db.delete_submission(doc_id)
            print(f"Deleted {len(to_delete)} entries")

        print(f"\nFinal database:")
        print(f"  Total documents: {db.get_collection_count()}")
        print(f"  All valid faculty with 2020+ publications")

        # Show final stats
        print("\n" + "="*80)
        print("COMPLETE!")
        print("="*80)
        print("\nYour database now contains:")
        print("  - Only valid faculty names (real people)")
        print("  - Only valid academic departments")
        print("  - Only publications from 2020 or later")
        print("\nStart the chatbot:")
        print("  python -m streamlit run app.py")

        crawler.close()

    finally:
        spider.close()


if __name__ == "__main__":
    try:
        run_smart_cs_spider()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
