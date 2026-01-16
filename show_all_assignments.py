"""
Show all department assignments for Unknown faculty
Complete list with reasoning
"""
import json

# Complete department assignments
DEPARTMENT_ASSIGNMENTS = {
    # ==========================================
    # EAST ASIAN LANGUAGES & CULTURES (6)
    # ==========================================
    'Honglan Huang': 'East Asian Languages & Cultures',
    'Kimiko Suzuki': 'East Asian Languages & Cultures',
    'Kin Cheung': 'East Asian Languages & Cultures',
    'Shizhe Huang': 'East Asian Languages & Cultures',
    'Tetsuya Sato': 'East Asian Languages & Cultures',
    'Yoko Koike': 'East Asian Languages & Cultures',
    # Reasoning: East Asian names + research in East Asian topics

    # ==========================================
    # SPANISH (5)
    # ==========================================
    'Ana López-Sánchez': 'Spanish',
    'Ariana Huberman': 'Spanish',
    'Aurelia Gómez De Unamuno': 'Spanish',
    'Israel Burshatin': 'Spanish',
    'Raquel Vieira Parrine Sant\'Ana': 'Spanish',
    # Reasoning: Spanish/Latin American names + publications in Hispanic studies

    # ==========================================
    # BIOLOGY (5)
    # ==========================================
    'Eman Al-Drous': 'Biology',
    'Imke Brust': 'Biology',
    'James Draney': 'Biology',
    'Kaitlyn Parenti': 'Biology',
    'Michael Burri': 'Biology',
    # Reasoning: Publications in biological sciences, ecology, molecular biology

    # ==========================================
    # FRENCH (2)
    # ==========================================
    'Koffi Anyinefa': 'French',
    'Marcel Gutwirth': 'French',
    # Reasoning: Publications in French literature and Francophone studies

    # ==========================================
    # LINGUISTICS (2)
    # ==========================================
    'Brook Lillehaugen': 'Linguistics',
    'Jane Chandlee': 'Linguistics',
    # Reasoning: Publications in linguistics, phonology, computational linguistics

    # ==========================================
    # COMPUTER SCIENCE (2)
    # ==========================================
    'Christopher R. Rogers': 'Computer Science',
    'Sara Mathieson': 'Computer Science',
    # Reasoning: Publications in computational methods, algorithms, bioinformatics

    # ==========================================
    # ENGLISH (2)
    # ==========================================
    'John Muse': 'English',
    'Sue Benston': 'English',
    # Reasoning: Publications in literature, cultural studies

    # ==========================================
    # FINE ARTS (2)
    # ==========================================
    'Graciela Michelotti': 'Fine Arts',
    'Indie Halstead': 'Fine Arts',
    # Reasoning: Publications in visual arts, art practice

    # ==========================================
    # HISTORY (2)
    # ==========================================
    'David Sedley': 'History',
    'Eriko Best': 'History',
    # Reasoning: Publications in historical topics

    # ==========================================
    # HISTORY OF ART (2)
    # ==========================================
    'Erin Schoneveld': 'History of Art',
    'Noah Elkins': 'History of Art',
    # Reasoning: Publications in art history, architectural history

    # ==========================================
    # PSYCHOLOGY (2)
    # ==========================================
    'Emily Black': 'Psychology',
    'Patrese Robinson-Drummer': 'Psychology',
    # Reasoning: Publications in neuroscience, behavioral psychology

    # ==========================================
    # RELIGION (2)
    # ==========================================
    'David Harrington Watt': 'Religion',
    'Hank Glassman': 'Religion',
    # Reasoning: Publications in religious studies, theology

    # ==========================================
    # SINGLE FACULTY ASSIGNMENTS (9)
    # ==========================================
    'Roberto Castillo Sandoval': 'Anthropology',
    'Kathryne Corbin': 'Chemistry',
    'Christophe Corbin': 'Classics',
    'Prea Persaud Khanna': 'Economics',
    'Ulrich Schönherr': 'German',
    'Luis Rodriguez-Rincon': 'Growth & Structure of Cities',
    'Carol Schilling': 'Music',
    'Jill Stauffer': 'Philosophy',
    'Gina Velasco': 'Sociology',

    # ==========================================
    # REMAIN UNKNOWN (13)
    # ==========================================
    'Anna West': 'Unknown',
    'Bethany Swann': 'Unknown',
    'Bryan Norton': 'Unknown',
    'Ezgi Guner': 'Unknown',
    'Jess Libow': 'Unknown',
    'Jessica Croteau': 'Unknown',
    'Kaye Edwards': 'Unknown',
    'Kevin Quin': 'Unknown',
    'Lauren Minsky': 'Unknown',
    'Lina Martinez Hernandez': 'Unknown',
    'Matthew O\'Hare': 'Unknown',
    'Michelle McGowan': 'Unknown',
    'Swetha Regunathan': 'Unknown',
    # Reasoning: No OpenAlex ID or insufficient publication data
}


def main():
    print("\n" + "="*80)
    print("COMPLETE DEPARTMENT ASSIGNMENTS")
    print("="*80 + "\n")

    # Load faculty data
    with open('haverford_faculty_with_openalex.json', 'r', encoding='utf-8') as f:
        faculty_data = json.load(f)

    unknown_faculty = [f for f in faculty_data if f.get('department') == 'Unknown']

    print(f"Starting: {len(unknown_faculty)} faculty with 'Unknown' department\n")

    # Group by new department
    by_dept = {}
    for faculty in unknown_faculty:
        name = faculty['name']
        new_dept = DEPARTMENT_ASSIGNMENTS.get(name, 'Unknown')

        if new_dept not in by_dept:
            by_dept[new_dept] = []

        by_dept[new_dept].append({
            'name': name,
            'openalex_id': faculty.get('openalex_id', 'None'),
            'works': faculty.get('works_count', 0)
        })

    # Display all assignments
    print("="*80)
    print("ASSIGNMENTS BY DEPARTMENT")
    print("="*80)

    # Sort departments alphabetically, but put Unknown last
    sorted_depts = sorted([d for d in by_dept.keys() if d != 'Unknown'])
    if 'Unknown' in by_dept:
        sorted_depts.append('Unknown')

    for dept in sorted_depts:
        print(f"\n{'='*80}")
        print(f"{dept} ({len(by_dept[dept])} faculty)")
        print('='*80)

        for faculty in sorted(by_dept[dept], key=lambda x: x['name']):
            print(f"\n  {faculty['name']}")
            if faculty['openalex_id'] != 'None':
                print(f"    OpenAlex ID: {faculty['openalex_id']}")
                print(f"    Works: {faculty['works']}")
            else:
                print(f"    No OpenAlex data")

    # Summary
    print("\n\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    assigned_count = sum(len(names) for dept, names in by_dept.items() if dept != 'Unknown')
    unknown_count = len(by_dept.get('Unknown', []))

    print(f"\nTotal faculty processed: {len(unknown_faculty)}")
    print(f"Successfully assigned: {assigned_count}")
    print(f"Remain unknown: {unknown_count}")

    print("\n" + "="*80)
    print("DEPARTMENT BREAKDOWN")
    print("="*80)

    for dept in sorted([d for d in by_dept.keys() if d != 'Unknown']):
        print(f"  {dept}: {len(by_dept[dept])}")

    if 'Unknown' in by_dept:
        print(f"  Unknown: {len(by_dept['Unknown'])}")

    print("\n" + "="*80)
    print("ASSIGNMENT CONFIDENCE")
    print("="*80)
    print("""
HIGH CONFIDENCE (based on clear publication patterns):
  - East Asian Languages & Cultures (6)
  - Spanish (5)
  - Biology (5)
  - French (2)
  - Linguistics (2)
  - Computer Science (2)

MEDIUM CONFIDENCE (based on limited publication data):
  - History (2)
  - History of Art (2)
  - Psychology (2)
  - Religion (2)
  - English (2)
  - Fine Arts (2)
  - All single-faculty assignments (9)

LOW CONFIDENCE (insufficient data):
  - Unknown (13) - require manual verification
""")


if __name__ == "__main__":
    main()
