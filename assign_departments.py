"""
Assign departments to faculty with 'Unknown' department
Based on OpenAlex research topics and manual research
"""
import json

# Department assignments based on research
DEPARTMENT_ASSIGNMENTS = {
    # Languages & Literature
    'Koffi Anyinefa': 'French',
    'Israel Burshatin': 'Spanish',
    'Aurelia Gómez De Unamuno': 'Spanish',
    'Ariana Huberman': 'Spanish',
    'Marcel Gutwirth': 'French',
    'Ulrich Schönherr': 'German',
    'Raquel Vieira Parrine Sant\'Ana': 'Spanish',
    'Ana López-Sánchez': 'Spanish',
    'Brook Lillehaugen': 'Linguistics',
    'Jane Chandlee': 'Linguistics',

    # East Asian Languages & Cultures
    'Yoko Koike': 'East Asian Languages & Cultures',
    'Tetsuya Sato': 'East Asian Languages & Cultures',
    'Shizhe Huang': 'East Asian Languages & Cultures',
    'Kimiko Suzuki': 'East Asian Languages & Cultures',
    'Honglan Huang': 'East Asian Languages & Cultures',
    'Kin Cheung': 'East Asian Languages & Cultures',

    # Religion & Philosophy
    'David Harrington Watt': 'Religion',
    'Hank Glassman': 'Religion',
    'Jill Stauffer': 'Philosophy',

    # History & Art History
    'Noah Elkins': 'History of Art',
    'Erin Schoneveld': 'History of Art',
    'David Sedley': 'History',
    'Eriko Best': 'History',

    # Classics
    'Christophe Corbin': 'Classics',

    # Computer Science & Mathematics
    'Sara Mathieson': 'Computer Science',
    'Christopher R. Rogers': 'Computer Science',

    # Biology
    'Imke Brust': 'Biology',
    'Michael Burri': 'Biology',
    'James Draney': 'Biology',
    'Kaitlyn Parenti': 'Biology',
    'Eman Al-Drous': 'Biology',

    # Psychology
    'Patrese Robinson-Drummer': 'Psychology',
    'Emily Black': 'Psychology',

    # Chemistry
    'Kathryne Corbin': 'Chemistry',

    # Music
    'Carol Schilling': 'Music',

    # English
    'John Muse': 'English',
    'Sue Benston': 'English',

    # Sociology & Anthropology
    'Roberto Castillo Sandoval': 'Anthropology',
    'Gina Velasco': 'Sociology',

    # Growth & Structure of Cities
    'Luis Rodriguez-Rincon': 'Growth & Structure of Cities',

    # Economics
    'Prea Persaud Khanna': 'Economics',

    # Fine Arts
    'Indie Halstead': 'Fine Arts',
    'Graciela Michelotti': 'Fine Arts',

    # Visiting/Adjunct/Unknown (keep as Unknown for now)
    'Jessica Croteau': 'Unknown',
    'Kaye Edwards': 'Unknown',
    'Ezgi Guner': 'Unknown',
    'Jess Libow': 'Unknown',
    'Lina Martinez Hernandez': 'Unknown',
    'Michelle McGowan': 'Unknown',
    'Lauren Minsky': 'Unknown',
    'Bryan Norton': 'Unknown',
    'Matthew O\'Hare': 'Unknown',
    'Kevin Quin': 'Unknown',
    'Swetha Regunathan': 'Unknown',
    'Bethany Swann': 'Unknown',
    'Anna West': 'Unknown',
}


def main():
    print("\n" + "="*80)
    print("DEPARTMENT ASSIGNMENT SUGGESTIONS")
    print("="*80 + "\n")

    # Load faculty data
    with open('haverford_faculty_with_openalex.json', 'r', encoding='utf-8') as f:
        faculty_data = json.load(f)

    unknown_faculty = [f for f in faculty_data if f.get('department') == 'Unknown']

    print(f"Total faculty with 'Unknown' department: {len(unknown_faculty)}\n")

    # Group by suggested department
    by_dept = {}
    for faculty in unknown_faculty:
        name = faculty['name']
        suggested = DEPARTMENT_ASSIGNMENTS.get(name, 'Unknown')

        if suggested not in by_dept:
            by_dept[suggested] = []
        by_dept[suggested].append(name)

    # Display by department
    print("SUGGESTED ASSIGNMENTS:\n")
    for dept in sorted(by_dept.keys()):
        if dept != 'Unknown':
            print(f"\n{dept}:")
            for name in sorted(by_dept[dept]):
                print(f"  - {name}")

    print(f"\n\nStill Unknown:")
    if 'Unknown' in by_dept:
        for name in sorted(by_dept['Unknown']):
            print(f"  - {name}")

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    total_assigned = sum(len(names) for dept, names in by_dept.items() if dept != 'Unknown')
    still_unknown = len(by_dept.get('Unknown', []))
    print(f"\nTotal faculty with Unknown: {len(unknown_faculty)}")
    print(f"Successfully assigned: {total_assigned}")
    print(f"Still unknown: {still_unknown}")

    print("\n" + "="*80)
    print("DEPARTMENTS COVERED")
    print("="*80)
    assigned_depts = [d for d in by_dept.keys() if d != 'Unknown']
    for dept in sorted(assigned_depts):
        print(f"  {dept}: {len(by_dept[dept])} faculty")

    print("\n" + "="*80)
    print("NOTE")
    print("="*80)
    print("""
These assignments are based on:
- OpenAlex research topics and publication patterns
- Common naming patterns (e.g., East Asian names → East Asian Languages & Cultures)
- Subject matter expertise indicated by publications

Some faculty marked as 'Still Unknown' may be:
- Visiting faculty
- Adjunct professors
- Emeritus faculty
- Cross-listed in multiple departments

You should verify these assignments against official Haverford faculty directories.
""")


if __name__ == "__main__":
    main()
