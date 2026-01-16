"""
Add 2025 faculty achievements to ChromaDB
"""
import json
import sys
from chroma_manager import ChromaDBManager

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

def main():
    print("\n" + "="*80)
    print("ADDING 2025 FACULTY ACHIEVEMENTS TO CHROMADB")
    print("="*80 + "\n")

    # Load 2025 achievements
    with open('faculty_achievements_2025.json', 'r', encoding='utf-8') as f:
        achievements = json.load(f)

    print(f"Loaded {len(achievements)} achievements from 2025 data\n")

    # Initialize ChromaDB
    chroma = ChromaDBManager()

    # Get faculty data for department verification
    with open('haverford_faculty_with_openalex.json', 'r', encoding='utf-8') as f:
        faculty_data = json.load(f)

    faculty_dept_map = {f['name']: f.get('department', 'Unknown') for f in faculty_data}

    # Prepare data for ChromaDB
    documents = []
    metadatas = []
    ids = []

    for i, achievement in enumerate(achievements):
        faculty_name = achievement['faculty_name']
        content_type = achievement['content_type']

        # Use provided department or lookup
        department = achievement.get('department', 'Unknown')
        if department == 'Unknown':
            department = faculty_dept_map.get(faculty_name, 'Unknown')

        # Create document text
        doc_parts = [
            f"Faculty: {faculty_name}",
            f"Department: {department}",
            f"Award: {achievement['title']}",
            f"Description: {achievement['description']}",
            f"Year: {achievement['year']}",
        ]

        if 'amount' in achievement:
            doc_parts.append(f"Amount: {achievement['amount']}")

        doc_parts.append(f"Source: {achievement['source']}")

        document = "\n".join(doc_parts)

        # Create metadata
        metadata = {
            'faculty_name': faculty_name,
            'department': department,
            'content_type': content_type,
            'date_published': achievement['date_published'],
            'title': achievement['title'],
            'source': achievement['source']
        }

        # Create unique ID
        doc_id = f"award_2025_{faculty_name.replace(' ', '_')}_{i}"

        documents.append(document)
        metadatas.append(metadata)
        ids.append(doc_id)

        print(f"  + [{content_type}] {faculty_name} - {achievement['title'][:60]}...")

    # Add to ChromaDB
    print(f"\nAdding {len(documents)} documents to ChromaDB...")
    chroma.add_documents(documents, metadatas, ids)

    # Verify
    print("\n" + "="*80)
    print("VERIFICATION")
    print("="*80)

    result = chroma.collection.get()
    all_metas = result['metadatas']

    content_type_counts = {}
    for meta in all_metas:
        ct = meta.get('content_type', 'Unknown')
        content_type_counts[ct] = content_type_counts.get(ct, 0) + 1

    print(f"\nTotal documents in ChromaDB: {len(result['ids'])}")
    print("\nBy content type:")
    for ct, count in sorted(content_type_counts.items()):
        print(f"  {ct}: {count}")

    # Show by department
    dept_counts = {}
    for meta in all_metas:
        if meta.get('content_type') == 'Award':
            dept = meta.get('department', 'Unknown')
            dept_counts[dept] = dept_counts.get(dept, 0) + 1

    print("\nAwards by department:")
    for dept, count in sorted(dept_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {dept}: {count}")

    print("\n✓ Successfully added 2025 achievements to ChromaDB")


if __name__ == "__main__":
    main()
