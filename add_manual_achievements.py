"""
Add manually extracted faculty achievements to ChromaDB
"""
import json
import sys
from chroma_manager import ChromaDBManager

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

def main():
    print("\n" + "="*80)
    print("ADDING MANUAL FACULTY ACHIEVEMENTS TO CHROMADB")
    print("="*80 + "\n")

    # Load manual achievements
    with open('faculty_achievements_manual.json', 'r', encoding='utf-8') as f:
        achievements = json.load(f)

    print(f"Loaded {len(achievements)} achievements from manual extraction\n")

    # Initialize ChromaDB
    chroma = ChromaDBManager()

    # Get faculty data for department lookup
    with open('haverford_faculty_with_openalex.json', 'r', encoding='utf-8') as f:
        faculty_data = json.load(f)

    faculty_dept_map = {f['name']: f.get('department', 'Unknown') for f in faculty_data}

    # Prepare data for ChromaDB
    documents = []
    metadatas = []
    ids = []

    for achievement in achievements:
        faculty_name = achievement['faculty_name']
        content_type = achievement['content_type']

        # Use department from achievement if available, otherwise lookup
        department = achievement.get('department')
        if not department or department == 'Unknown':
            department = faculty_dept_map.get(faculty_name, 'Unknown')

        # Create document text
        if content_type == 'Award':
            document = f"""
Faculty: {faculty_name}
Department: {department}
Award: {achievement['title']}
Description: {achievement['description']}
Year: {achievement['year']}
Source: {achievement['source']}
""".strip()
        elif content_type == 'Talk':
            document = f"""
Faculty: {faculty_name}
Department: {department}
Presentation: {achievement['title']}
Description: {achievement['description']}
Year: {achievement['year']}
Source: {achievement['source']}
""".strip()
        else:
            document = f"""
Faculty: {faculty_name}
Department: {department}
Title: {achievement['title']}
Description: {achievement['description']}
Year: {achievement['year']}
Source: {achievement['source']}
""".strip()

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
        doc_id = f"{content_type.lower()}_{faculty_name.replace(' ', '_')}_{achievement['year']}_{len(documents)}"

        documents.append(document)
        metadatas.append(metadata)
        ids.append(doc_id)

        print(f"  + [{content_type}] {faculty_name} - {achievement['title']}")

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

    print("\n✓ Successfully added manual achievements to ChromaDB")


if __name__ == "__main__":
    main()
