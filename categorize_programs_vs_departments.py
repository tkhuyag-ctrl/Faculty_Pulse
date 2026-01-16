"""
Categorize faculty into Departments vs Programs
Programs at Haverford include interdisciplinary programs that are not traditional departments
"""
import json

# Programs (not traditional departments)
PROGRAMS = [
    'Growth & Structure of Cities',
    'Linguistics',
    'East Asian Languages & Cultures',
    'Environmental Studies',
    'Africana Studies',
    'Gender and Sexuality Studies',
    'Health Studies',
    'Latin American, Iberian, and Latina/o Studies',
    'Middle Eastern and Islamic Studies',
    'Neural and Behavioral Sciences',
    'Peace, Justice, and Human Rights',
    'Scientific Computing'
]

# Traditional Departments
DEPARTMENTS = [
    'Anthropology',
    'Astronomy',
    'Biology',
    'Chemistry',
    'Classics',
    'Computer Science',
    'Economics',
    'English',
    'Fine Arts',
    'French',
    'Geology',
    'German',
    'History',
    'History of Art',
    'Mathematics',
    'Music',
    'Philosophy',
    'Physics',
    'Political Science',
    'Psychology',
    'Religion',
    'Sociology',
    'Spanish',
    'Mathematics & Statistics'
]

# Reassignments for Unknown faculty
DEPARTMENT_ASSIGNMENTS = {
    # Move to Programs
    'Luis Rodriguez-Rincon': 'Program',  # Growth & Structure of Cities
    'Brook Lillehaugen': 'Program',  # Linguistics
    'Jane Chandlee': 'Program',  # Linguistics
    'Honglan Huang': 'Program',  # East Asian Languages & Cultures
    'Kimiko Suzuki': 'Program',  # East Asian Languages & Cultures
    'Kin Cheung': 'Program',  # East Asian Languages & Cultures
    'Shizhe Huang': 'Program',  # East Asian Languages & Cultures
    'Tetsuya Sato': 'Program',  # East Asian Languages & Cultures
    'Yoko Koike': 'Program',  # East Asian Languages & Cultures

    # Assign to Departments
    'Koffi Anyinefa': 'French',
    'Israel Burshatin': 'Spanish',
    'Aurelia Gómez De Unamuno': 'Spanish',
    'Ariana Huberman': 'Spanish',
    'Marcel Gutwirth': 'French',
    'Ulrich Schönherr': 'German',
    'Raquel Vieira Parrine Sant\'Ana': 'Spanish',
    'Ana López-Sánchez': 'Spanish',
    'David Harrington Watt': 'Religion',
    'Hank Glassman': 'Religion',
    'Jill Stauffer': 'Philosophy',
    'Noah Elkins': 'History of Art',
    'Erin Schoneveld': 'History of Art',
    'David Sedley': 'History',
    'Eriko Best': 'History',
    'Christophe Corbin': 'Classics',
    'Sara Mathieson': 'Computer Science',
    'Christopher R. Rogers': 'Computer Science',
    'Imke Brust': 'Biology',
    'Michael Burri': 'Biology',
    'James Draney': 'Biology',
    'Kaitlyn Parenti': 'Biology',
    'Eman Al-Drous': 'Biology',
    'Patrese Robinson-Drummer': 'Psychology',
    'Emily Black': 'Psychology',
    'Kathryne Corbin': 'Chemistry',
    'Carol Schilling': 'Music',
    'John Muse': 'English',
    'Sue Benston': 'English',
    'Roberto Castillo Sandoval': 'Anthropology',
    'Gina Velasco': 'Sociology',
    'Prea Persaud Khanna': 'Economics',
    'Indie Halstead': 'Fine Arts',
    'Graciela Michelotti': 'Fine Arts',

    # Keep as Unknown (visiting/adjunct)
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
    print("CATEGORIZE: DEPARTMENTS vs PROGRAMS")
    print("="*80 + "\n")

    # Load faculty data
    with open('haverford_faculty_with_openalex.json', 'r', encoding='utf-8') as f:
        faculty_data = json.load(f)

    unknown_faculty = [f for f in faculty_data if f.get('department') == 'Unknown']

    # Categorize
    by_category = {
        'Department': {},
        'Program': [],
        'Unknown': []
    }

    for faculty in unknown_faculty:
        name = faculty['name']
        assignment = DEPARTMENT_ASSIGNMENTS.get(name, 'Unknown')

        if assignment == 'Program':
            by_category['Program'].append(name)
        elif assignment == 'Unknown':
            by_category['Unknown'].append(name)
        else:  # It's a department
            if assignment not in by_category['Department']:
                by_category['Department'][assignment] = []
            by_category['Department'][assignment].append(name)

    # Display results
    print("="*80)
    print("FACULTY IN PROGRAMS (Interdisciplinary)")
    print("="*80 + "\n")
    print("These faculty will be categorized as 'Program' instead of a specific department:")
    print()
    for name in sorted(by_category['Program']):
        print(f"  - {name}")
    print(f"\nTotal: {len(by_category['Program'])} faculty")

    print("\n" + "="*80)
    print("FACULTY IN TRADITIONAL DEPARTMENTS")
    print("="*80 + "\n")
    for dept in sorted(by_category['Department'].keys()):
        print(f"\n{dept}:")
        for name in sorted(by_category['Department'][dept]):
            print(f"  - {name}")

    total_dept = sum(len(names) for names in by_category['Department'].values())
    print(f"\nTotal: {total_dept} faculty")

    print("\n" + "="*80)
    print("STILL UNKNOWN (Visiting/Adjunct)")
    print("="*80 + "\n")
    for name in sorted(by_category['Unknown']):
        print(f"  - {name}")
    print(f"\nTotal: {len(by_category['Unknown'])} faculty")

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"\nTotal Unknown faculty: {len(unknown_faculty)}")
    print(f"  → Program faculty: {len(by_category['Program'])}")
    print(f"  → Department faculty: {total_dept}")
    print(f"  → Still Unknown: {len(by_category['Unknown'])}")

    print("\n" + "="*80)
    print("PROGRAMS AT HAVERFORD")
    print("="*80)
    print("\nInterdisciplinary programs (faculty will be marked as 'Program'):")
    for prog in sorted(PROGRAMS):
        print(f"  - {prog}")

    print("\n" + "="*80)
    print("IMPLEMENTATION NOTE")
    print("="*80)
    print("""
When updating the database, faculty in interdisciplinary programs will have:
  - department: 'Program'

This allows you to filter by:
  - Traditional academic departments (Biology, English, etc.)
  - Interdisciplinary programs (as a single category)
  - Unknown (visiting/adjunct faculty)

Examples of queries:
  - "Show me all department faculty" → excludes programs
  - "Show me program faculty" → shows interdisciplinary programs only
  - "Show me all faculty" → includes everyone
""")


if __name__ == "__main__":
    main()
