"""
Show exactly who has Unknown department
With corrected understanding that East Asian Languages & Cultures,
Growth & Structure of Cities, Geology, and Archaeology are DEPARTMENTS
"""
import json

# Updated department assignments
DEPARTMENT_ASSIGNMENTS = {
    # East Asian Languages & Cultures (DEPARTMENT)
    'Honglan Huang': 'East Asian Languages & Cultures',
    'Kimiko Suzuki': 'East Asian Languages & Cultures',
    'Kin Cheung': 'East Asian Languages & Cultures',
    'Shizhe Huang': 'East Asian Languages & Cultures',
    'Tetsuya Sato': 'East Asian Languages & Cultures',
    'Yoko Koike': 'East Asian Languages & Cultures',

    # Growth & Structure of Cities (DEPARTMENT)
    'Luis Rodriguez-Rincon': 'Growth & Structure of Cities',

    # Linguistics (PROGRAM - keep separate)
    'Brook Lillehaugen': 'Linguistics',
    'Jane Chandlee': 'Linguistics',

    # Language Departments
    'Koffi Anyinefa': 'French',
    'Israel Burshatin': 'Spanish',
    'Aurelia Gómez De Unamuno': 'Spanish',
    'Ariana Huberman': 'Spanish',
    'Marcel Gutwirth': 'French',
    'Ulrich Schönherr': 'German',
    'Raquel Vieira Parrine Sant\'Ana': 'Spanish',
    'Ana López-Sánchez': 'Spanish',

    # Religion & Philosophy
    'David Harrington Watt': 'Religion',
    'Hank Glassman': 'Religion',
    'Jill Stauffer': 'Philosophy',

    # History & Art History
    'Noah Elkins': 'History of Art',
    'Erin Schoneveld': 'History of Art',
    'David Sedley': 'History',
    'Eriko Best': 'History',

    # Classics & Archaeology
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

    # Economics
    'Prea Persaud Khanna': 'Economics',

    # Fine Arts
    'Indie Halstead': 'Fine Arts',
    'Graciela Michelotti': 'Fine Arts',

    # Keep as Unknown (visiting/adjunct/not enough info)
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
    print("EXACT UNKNOWN FACULTY LIST")
    print("="*80 + "\n")

    # Load faculty data
    with open('haverford_faculty_with_openalex.json', 'r', encoding='utf-8') as f:
        faculty_data = json.load(f)

    unknown_in_file = [f for f in faculty_data if f.get('department') == 'Unknown']

    print(f"Total faculty with 'Unknown' in file: {len(unknown_in_file)}\n")

    # Categorize by assignment
    assigned = {}
    still_unknown = []

    for faculty in unknown_in_file:
        name = faculty['name']
        assignment = DEPARTMENT_ASSIGNMENTS.get(name, 'Unknown')

        if assignment == 'Unknown':
            still_unknown.append({
                'name': name,
                'openalex_id': faculty.get('openalex_id', 'N/A'),
                'works_count': faculty.get('works_count', 0)
            })
        else:
            if assignment not in assigned:
                assigned[assignment] = []
            assigned[assignment].append(name)

    # Show assigned
    print("="*80)
    print("FACULTY THAT CAN BE ASSIGNED")
    print("="*80 + "\n")

    for dept in sorted(assigned.keys()):
        print(f"\n{dept}:")
        for name in sorted(assigned[dept]):
            print(f"  - {name}")

    total_assigned = sum(len(names) for names in assigned.values())
    print(f"\n\nTotal assignable: {total_assigned} faculty")

    # Show truly unknown
    print("\n" + "="*80)
    print("TRULY UNKNOWN FACULTY")
    print("="*80)
    print("\nThese faculty cannot be confidently assigned to a department:")
    print("(May be visiting faculty, adjuncts, or cross-listed)\n")

    for faculty_info in sorted(still_unknown, key=lambda x: x['name']):
        print(f"  - {faculty_info['name']}")
        print(f"    OpenAlex ID: {faculty_info['openalex_id']}")
        print(f"    Works count: {faculty_info['works_count']}")

    print(f"\n\nTotal truly unknown: {len(still_unknown)} faculty")

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"\nStarting with: {len(unknown_in_file)} faculty marked 'Unknown'")
    print(f"Can be assigned: {total_assigned} faculty")
    print(f"Remain unknown: {len(still_unknown)} faculty")

    print("\n" + "="*80)
    print("DEPARTMENTS WITH NEW ASSIGNMENTS")
    print("="*80)
    for dept in sorted(assigned.keys()):
        print(f"  {dept}: {len(assigned[dept])} faculty")


if __name__ == "__main__":
    main()
