"""
Simple database statistics viewer
"""
from chroma_manager import ChromaDBManager
from collections import Counter

print("="*80)
print("FACULTY PULSE DATABASE - CURRENT STATUS")
print("="*80)

db = ChromaDBManager()

# Get all data
all_data = db.get_all_submissions()
total = len(all_data['ids'])

print(f"\nTotal Documents: {total}")

if total == 0:
    print("\nDatabase is empty!")
    print("\nTo populate:")
    print("  1. Run: python run_haverford_spider.py")
    print("  2. Then: python cleanup_and_load.py")
else:
    # Analyze content
    departments = Counter()
    content_types = Counter()
    faculty_names = Counter()
    years = Counter()

    for metadata in all_data['metadatas']:
        departments[metadata.get('department', 'Unknown')] += 1
        content_types[metadata.get('content_type', 'Unknown')] += 1
        faculty_names[metadata.get('faculty_name', 'Unknown')] += 1

        # Extract year
        date_str = metadata.get('date_published', '')
        try:
            year = date_str.split('-')[0]
            if year.isdigit():
                years[year] += 1
        except:
            pass

    print("\nBy Department:")
    for dept, count in departments.most_common():
        print(f"  {dept}: {count}")

    print("\nBy Content Type:")
    for ctype, count in content_types.most_common():
        print(f"  {ctype}: {count}")

    print("\nBy Year:")
    for year, count in sorted(years.items(), reverse=True):
        print(f"  {year}: {count}")

    print(f"\nUnique Faculty Members: {len(faculty_names)}")
    print("\nTop 5 Faculty (by document count):")
    for name, count in faculty_names.most_common(5):
        print(f"  {name}: {count} document(s)")

print("\n" + "="*80)
print("DATABASE IS READY!")
print("="*80)
print("\nStart the chatbot:")
print("  python -m streamlit run app.py")
print("\nOr run in background:")
print("  start /b python -m streamlit run app.py")
