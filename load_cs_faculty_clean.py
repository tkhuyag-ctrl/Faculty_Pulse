"""
Load CS Faculty with Clean Validation
- Only valid person names
- Only valid departments
- Only 2020+ publications
"""
import json
import re
from datetime import datetime
from automated_crawler import AutomatedCrawler
from chroma_manager import ChromaDBManager

def is_valid_person_name(name: str) -> bool:
    """Check if name looks like a real person's name"""
    if not name or name == "Unknown Faculty":
        return False

    non_person_keywords = [
        'scholarship', 'repository', 'college', 'university',
        'department', 'school', 'publications', 'cs department'
    ]

    name_lower = name.lower()
    for keyword in non_person_keywords:
        if keyword in name_lower:
            return False

    name_parts = [p for p in name.split() if len(p) > 1]
    if len(name_parts) < 2 or len(name_parts) > 5:
        return False

    return True

def is_valid_department(department: str) -> bool:
    """Check if department is valid"""
    if not department or department == "Unknown Department":
        return False

    valid_departments = [
        'computer science', 'cs', 'biology', 'chemistry', 'physics',
        'mathematics', 'math', 'psychology', 'economics', 'philosophy',
        'history', 'english', 'classics', 'linguistics', 'political science'
    ]

    dept_lower = department.lower()
    return any(valid_dept in dept_lower for valid_dept in valid_departments)

def extract_year_from_content(content: str) -> int:
    """Extract year from content"""
    year_pattern = r'\b(202[0-6])\b'
    match = re.search(year_pattern, content)
    if match:
        return int(match.group(1))
    return None

print("="*80)
print("CLEAN CS FACULTY LOADER")
print("="*80)

# Step 1: Load and crawl URLs
print("\nStep 1: Crawling CS faculty URLs...")
crawler = AutomatedCrawler()

try:
    crawler.load_urls_from_json('cs_faculty_urls.json')
    print(f"Loaded URLs from cs_faculty_urls.json")

    print("\nCrawling... (this may take a few minutes)")
    results = crawler.crawl_all_pending()

    print(f"\nCrawl Results:")
    print(f"  Successful: {results['successful']}/{results['total']}")
    print(f"  Failed: {results['failed']}")

    # Step 2: Clean database
    print("\n" + "="*80)
    print("Step 2: Cleaning database...")
    print("="*80)

    db = ChromaDBManager()
    all_data = db.get_all_submissions()

    to_delete = []
    kept_valid = []

    for doc_id, doc, metadata in zip(
        all_data['ids'],
        all_data['documents'],
        all_data['metadatas']
    ):
        faculty_name = metadata.get('faculty_name', '')
        department = metadata.get('department', '')
        date_published = metadata.get('date_published', '')

        # Validate name
        if not is_valid_person_name(faculty_name):
            print(f"  Removing (invalid name): {faculty_name}")
            to_delete.append(doc_id)
            continue

        # Validate department
        if not is_valid_department(department):
            print(f"  Removing (invalid dept): {department}")
            to_delete.append(doc_id)
            continue

        # Check year
        try:
            year = datetime.fromisoformat(date_published.replace('Z', '+00:00')).year
        except:
            year = extract_year_from_content(doc)

        if not year or year < 2020:
            print(f"  Removing (pre-2020): {faculty_name}")
            to_delete.append(doc_id)
            continue

        kept_valid.append({
            'faculty': faculty_name,
            'department': department,
            'year': year
        })

    # Delete invalid entries
    if to_delete:
        print(f"\nDeleting {len(to_delete)} invalid entries...")
        for doc_id in to_delete:
            db.delete_submission(doc_id)

    # Show results
    print("\n" + "="*80)
    print("FINAL DATABASE")
    print("="*80)
    print(f"Total documents: {db.get_collection_count()}")

    if kept_valid:
        print("\nValid Faculty Entries:")
        from collections import Counter
        by_faculty = Counter(entry['faculty'] for entry in kept_valid)
        by_dept = Counter(entry['department'] for entry in kept_valid)

        print("\nBy Faculty:")
        for faculty, count in by_faculty.most_common():
            print(f"  {faculty}: {count} document(s)")

        print("\nBy Department:")
        for dept, count in by_dept.most_common():
            print(f"  {dept}: {count} document(s)")

    print("\n" + "="*80)
    print("COMPLETE!")
    print("="*80)
    print("\nDatabase now contains:")
    print("  - Only valid faculty names (real people)")
    print("  - Only valid academic departments")
    print("  - Only publications from 2020+")
    print("\nStart the chatbot:")
    print("  python -m streamlit run app.py")

finally:
    crawler.close()
