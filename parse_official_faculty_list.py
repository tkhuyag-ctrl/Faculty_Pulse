"""
Parse the official Haverford faculty list and assign correct departments
Based on the official list provided by the user
"""
import json
import re
import sys

# Fix encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Official faculty list from Haverford website
OFFICIAL_FACULTY_LIST = """
Jenea Adams Visiting Assistant Professor of Biology
Karin Åkerfeldt Professor Emeritus of Chemistry
Eman Al-Drous Visiting Assistant Professor of Biology
Hakan Altindag Assistant Professor of Economics
Koffi Anyinefa Professor Emeritus of French
Jonathan Ashmore Professor of Physics
Norbert Baer Visiting Professor of Fine Arts
Steve Banta Professor of Chemistry
Anita Barvenko Lecturer in Russian and Director of the Russian Language Program
Carol Bazemore-James Associate Librarian
Renee Bent Visiting Lecturer of Africana Studies
Asmaou Bah Bello Visiting Assistant Professor of Growth & Structure of Cities
Sue Benston Professor of English
Fran Blase Provost's Postdoctoral Fellow in Physics
Erica Blom Assistant Professor of Linguistics and Director of the Haverford Writing Program
Rachel Buurma Associate Professor of English
Lisa Beal Professor of Biology
Emily Black Visiting Assistant Professor of Psychology
Amardeep Bhandal Visiting Associate Professor of Political Science
Eriko Best Visiting Assistant Professor of History
Gabriel Brauner Associate Professor of Physics
Pauline Breuze Lecturer in French and Francophone Studies
Austin Brinkman Lecturer in Mathematics and Statistics
Roberto Castillo Sandoval Visiting Assistant Professor of Anthropology
Mel Chua Visiting Assistant Professor of Engineering
Brook Lillehaugen Associate Professor of Linguistics
Imke Brust Visiting Assistant Professor of Biology
Michael Burri Visiting Assistant Professor of Biology
Israel Burshatin Professor Emeritus of Spanish
Emma Burgess Visiting Assistant Professor of Fine Arts
Jane Chandlee Assistant Professor of Linguistics
Kin Cheung Visiting Assistant Professor of East Asian Languages & Cultures
Paul Jefferson Professor of Physics
Jonathan Cohn Assistant Professor of Computer Science
David Golland Associate Dean and Director for Center for Peace and Global Citizenship
Christine Comfort Visiting Instructor of Italian
Kathryne Corbin Visiting Assistant Professor of Chemistry
Christophe Corbin Visiting Assistant Professor of Classics
Jessica Croteau Visiting Assistant Professor of Sociology
Liliana Deyro Associate Professor of Fine Arts
Laura Dudley Jenkins Professor of Political Science
Susanna Fioratta Associate Professor of Anthropology
Justin Biel Assistant Professor of Mathematics and Statistics
Danielle Dodoo Assistant Professor of History
James Draney Visiting Assistant Professor of Biology
Catherine Engel Associate Dean for Academic Affairs
Richard Freedman John C. Whitehead Professor of Humanities and Chair, Music
John Chesick Visiting Professor of Physics
Laura Garcia-Reyes Assistant Professor of Spanish
Hank Glassman Professor of Religion
Aurelia Gómez De Unamuno Visiting Associate Professor of Spanish
Ana López-Sánchez Visiting Assistant Professor of Spanish
Nathan Graber Visiting Instructor of Physics
Krista Gromalski Postdoctoral Fellow
Ezgi Guner Lecturer in French
Zach Herrmann Postdoctoral Fellow
Tyler Jo Smith Professor of History of Art
Marcel Gutwirth Professor Emeritus of French
Shizhe Huang Visiting Assistant Professor of East Asian Languages & Cultures
Indie Halstead Visiting Assistant Professor of Fine Arts
Chloe Harris Lecturer in French
Honglan Huang Visiting Assistant Professor of East Asian Languages & Cultures
Ariana Huberman Professor of Spanish
Sam Hyeon Postdoctoral Fellow
Nora Perrone Visiting Assistant Professor of Classics
Karina Pallagst Provost's Postdoctoral Fellow
Catherine Keller Visiting Instructor of Chemistry
Prea Persaud Khanna Visiting Assistant Professor of Economics
Yoko Koike Visiting Assistant Professor of East Asian Languages & Cultures
Jess Libow Postdoctoral Fellow
Lina Martinez Hernandez Visiting Assistant Professor of Sociology
Sara Mathieson Associate Professor of Computer Science
Michelle McGowan Lecturer in Italian
Laurel Caryn Schneider Professor of Religious Studies and Gender & Sexuality Studies
Stephen McMullin Assistant Professor of Biology
Graciela Michelotti Visiting Assistant Professor of Fine Arts
Lauren Minsky Visiting Instructor of Fine Arts
Amanda Moniz Professor of History
John Muse Associate Professor of English
Bryan Norton Postdoctoral Fellow
Matthew O'Hare Visiting Assistant Professor of Computer Science
Mick O'Shea Lecturer in Psychology
Kaitlyn Parenti Visiting Assistant Professor of Biology
Ryan Perry Professor of English
Julia Byers Postdoctoral Fellow
Helen Plotkin Lecturer in English
Kevin Quin Postdoctoral Fellow
Anna Rabil Postdoctoral Fellow
Steven Rambach Lecturer in Physics
Swetha Regunathan Postdoctoral Fellow
Wendy Sternberg Professor of Biology
David Rein Associate Professor of Biology
Patrese Robinson-Drummer Visiting Assistant Professor of Psychology
Luis Rodriguez-Rincon Visiting Assistant Professor of Growth & Structure of Cities
Christopher R. Rogers Visiting Assistant Professor of Computer Science
Carol Schilling Visiting Lecturer in Music
Ulrich Schönherr Associate Professor of German
Tetsuya Sato Visiting Assistant Professor of East Asian Languages & Cultures
Erin Schoneveld Visiting Assistant Professor of History of Art
Noah Elkins Visiting Assistant Professor of History of Art
Karen Schultz Professor of Biology
David Sedley Visiting Associate Professor of History
Kaye Edwards Visiting Professor of Music
Eric Shea-Brown Visiting Professor of Computer Science
Brandon Schmitt Provost's Postdoctoral Fellow
Joshua Ramey Associate Professor of Philosophy
Linda Gerstein Professor Emeritus of Fine Arts
Jill Stauffer Professor of Philosophy
Kimiko Suzuki Visiting Assistant Professor of East Asian Languages & Cultures
Bethany Swann Postdoctoral Fellow
Nico Slate Professor of History
Richard Thomas David Pinkerton Professor of Classics
William Hohenstein Professor of Chemistry
Joel Rosenthal Henry S. Coleman Professor of Chemistry
Helen White Associate Professor of Psychology
Rob Fairman Professor of Chemistry
David Dawson Visiting Instructor of Chemistry
Gina Velasco Visiting Assistant Professor of Sociology
Raquel Vieira Parrine Sant'Ana Visiting Assistant Professor of Spanish
David Harrington Watt Professor of Religion
Anna West Postdoctoral Fellow
"""


def parse_faculty_entry(line):
    """
    Parse a faculty entry to extract name and department

    Format examples:
    - "Jenea Adams Visiting Assistant Professor of Biology"
    - "Karin Åkerfeldt Professor Emeritus of Chemistry"
    - "David Golland Associate Dean and Director for Center for Peace and Global Citizenship"
    """
    line = line.strip()
    if not line:
        return None, None

    # Common title patterns to identify where name ends
    title_patterns = [
        r'\bProfessor\b',
        r'\bAssociate Professor\b',
        r'\bAssistant Professor\b',
        r'\bVisiting Professor\b',
        r'\bVisiting Associate Professor\b',
        r'\bVisiting Assistant Professor\b',
        r'\bProfessor Emeritus\b',
        r'\bLecturer\b',
        r'\bVisiting Lecturer\b',
        r'\bVisiting Instructor\b',
        r'\bInstructor\b',
        r'\bPostdoctoral Fellow\b',
        r'\bProvost\'s Postdoctoral Fellow\b',
        r'\bAssociate Dean\b',
        r'\bDean\b',
        r'\bDirector\b',
        r'\bLibrarian\b',
        r'\bAssociate Librarian\b',
    ]

    # Find where the title starts
    title_match = None
    for pattern in title_patterns:
        match = re.search(pattern, line)
        if match:
            if title_match is None or match.start() < title_match.start():
                title_match = match

    if not title_match:
        return None, None

    # Extract name (everything before title)
    name = line[:title_match.start()].strip()

    # Extract title and department (everything from title onwards)
    title_and_dept = line[title_match.start():].strip()

    # Try to extract department from title
    # Pattern 1: "... of [Department]"
    dept_match = re.search(r'\bof\s+(.+?)$', title_and_dept)
    if dept_match:
        department = dept_match.group(1).strip()
        return name, department

    # Pattern 2: "... in [Department]"
    dept_match = re.search(r'\bin\s+(.+?)$', title_and_dept)
    if dept_match:
        department = dept_match.group(1).strip()
        return name, department

    # Pattern 3: "... for [Center/Program]"
    dept_match = re.search(r'\bfor\s+(.+?)$', title_and_dept)
    if dept_match:
        department = dept_match.group(1).strip()
        return name, department

    # Pattern 4: "... and [Role]" - extract department from role
    if "Associate Dean" in title_and_dept or "Dean" in title_and_dept:
        # Administrative role - might not have a department
        return name, "Administration"

    # If no department found
    return name, "Unknown"


def normalize_department_name(dept):
    """Normalize department names to match existing data"""
    if not dept or dept == "Unknown":
        return "Unknown"

    # Common normalizations
    normalizations = {
        "the Russian Language Program": "Russian",
        "Africana Studies": "Africana Studies",
        "the Haverford Writing Program": "Writing Program",
        "French and Francophone Studies": "French",
        "East Asian Languages & Cultures": "East Asian Languages & Cultures",
        "Mathematics and Statistics": "Mathematics",
        "Linguistics": "Linguistics",
        "Computer Science": "Computer Science",
        "Center for Peace and Global Citizenship": "CPGC",
        "Religious Studies and Gender & Sexuality Studies": "Religion",
        "History of Art": "History of Art",
        "Growth & Structure of Cities": "Growth & Structure of Cities",
    }

    for key, value in normalizations.items():
        if key in dept:
            return value

    return dept


def main():
    print("\n" + "="*80)
    print("PARSING OFFICIAL HAVERFORD FACULTY LIST")
    print("="*80 + "\n")

    # Parse the official list
    faculty_assignments = {}
    lines = OFFICIAL_FACULTY_LIST.strip().split('\n')

    print(f"Processing {len(lines)} faculty entries...\n")

    for line in lines:
        name, department = parse_faculty_entry(line)
        if name:
            department = normalize_department_name(department)
            faculty_assignments[name] = department
            print(f"{name:40} → {department}")

    print(f"\n\nParsed {len(faculty_assignments)} faculty members")

    # Load existing faculty data
    with open('haverford_faculty_with_openalex.json', 'r', encoding='utf-8') as f:
        faculty_data = json.load(f)

    print(f"Loaded {len(faculty_data)} faculty from database")

    # Match and update
    matches = 0
    updates = 0
    unknown_before = 0
    unknown_after = 0

    for faculty in faculty_data:
        name = faculty['name']
        old_dept = faculty.get('department', 'Unknown')

        if old_dept == 'Unknown':
            unknown_before += 1

        # Try exact match
        if name in faculty_assignments:
            new_dept = faculty_assignments[name]
            if old_dept != new_dept:
                faculty['department'] = new_dept
                updates += 1
                print(f"✓ Updated: {name:40} {old_dept:30} → {new_dept}")
            matches += 1

        if faculty.get('department', 'Unknown') == 'Unknown':
            unknown_after += 1

    print("\n" + "="*80)
    print("UPDATE SUMMARY")
    print("="*80)
    print(f"\nTotal faculty in database: {len(faculty_data)}")
    print(f"Matched with official list: {matches}")
    print(f"Department updates made: {updates}")
    print(f"Unknown before: {unknown_before}")
    print(f"Unknown after: {unknown_after}")
    print(f"Resolved: {unknown_before - unknown_after}")

    # Save updated data
    with open('haverford_faculty_with_openalex_updated.json', 'w', encoding='utf-8') as f:
        json.dump(faculty_data, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Saved updated data to: haverford_faculty_with_openalex_updated.json")

    # Show departments breakdown
    print("\n" + "="*80)
    print("DEPARTMENTS BREAKDOWN")
    print("="*80)

    dept_counts = {}
    for faculty in faculty_data:
        dept = faculty.get('department', 'Unknown')
        dept_counts[dept] = dept_counts.get(dept, 0) + 1

    for dept in sorted(dept_counts.keys()):
        print(f"{dept:40} {dept_counts[dept]:3} faculty")

    # Show remaining unknown
    print("\n" + "="*80)
    print("REMAINING UNKNOWN FACULTY")
    print("="*80)

    unknown_faculty = [f for f in faculty_data if f.get('department') == 'Unknown']
    for faculty in unknown_faculty:
        print(f"  - {faculty['name']}")
        if faculty.get('openalex_id'):
            print(f"    OpenAlex ID: {faculty['openalex_id']}")
            print(f"    Works: {faculty.get('works_count', 0)}")

    print(f"\nTotal remaining unknown: {len(unknown_faculty)}")


if __name__ == "__main__":
    main()
