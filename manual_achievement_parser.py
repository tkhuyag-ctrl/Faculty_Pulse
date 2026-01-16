"""
Manual achievement parser
Paste HTML content or text from faculty update pages
This script will extract and structure the achievements
"""
import sys
import json
import re
from datetime import datetime

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')


def parse_achievement_entry(text):
    """Parse a single achievement entry"""
    # Common patterns:
    # "Name (Department) received/won/presented..."
    # "Name, Department, received/won..."

    achievement_keywords = {
        'Award': ['award', 'grant', 'fellowship', 'prize', 'honor', 'received', 'won', 'named', 'selected'],
        'Talk': ['presented', 'talk', 'keynote', 'lecture', 'conference', 'symposium', 'panel', 'spoke'],
        'Publication': ['published', 'book', 'article', 'paper', 'journal', 'chapter', 'co-authored', 'edited']
    }

    text_lower = text.lower()

    # Determine content type
    content_type = 'Unknown'
    for ctype, keywords in achievement_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            content_type = ctype
            break

    return {
        'text': text,
        'content_type': content_type,
        'raw': text
    }


def extract_faculty_name(text):
    """Try to extract faculty name from text"""
    # Pattern: Name at start, often followed by (Department) or comma
    # or with title like "Professor Name"

    # Try to find name before parenthesis or comma
    match = re.match(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)[\s,\(]', text)
    if match:
        return match.group(1)

    # Try to find name after title
    title_pattern = r'(?:Professor|Associate Professor|Assistant Professor|Visiting Professor|Dr\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)'
    match = re.search(title_pattern, text)
    if match:
        return match.group(1)

    return None


def main():
    print("\n" + "="*80)
    print("MANUAL ACHIEVEMENT PARSER")
    print("="*80)
    print("\nPaste the text content from faculty update pages below.")
    print("Press Ctrl+D (or Ctrl+Z on Windows) when done, or type 'DONE' on a new line.\n")
    print("-"*80 + "\n")

    lines = []
    try:
        while True:
            line = input()
            if line.strip() == 'DONE':
                break
            lines.append(line)
    except EOFError:
        pass

    full_text = '\n'.join(lines)

    print("\n" + "="*80)
    print("PARSING...")
    print("="*80 + "\n")

    # Split into paragraphs
    paragraphs = [p.strip() for p in full_text.split('\n\n') if p.strip()]

    achievements = []

    for para in paragraphs:
        # Skip very short paragraphs
        if len(para) < 30:
            continue

        # Check if it contains achievement keywords
        para_lower = para.lower()
        has_achievement = any(keyword in para_lower for keyword in
                             ['award', 'grant', 'fellowship', 'prize', 'presented',
                              'talk', 'published', 'book', 'received', 'won'])

        if has_achievement:
            achievement = parse_achievement_entry(para)
            faculty_name = extract_faculty_name(para)

            achievement['faculty_name'] = faculty_name or 'Unknown'

            achievements.append(achievement)
            print(f"[{achievement['content_type']}] {faculty_name or 'Unknown'}")
            print(f"  {para[:100]}...")
            print()

    # Save to JSON
    output_file = f'manual_achievements_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(achievements, f, indent=2, ensure_ascii=False)

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"\nTotal achievements found: {len(achievements)}")

    # Count by type
    type_counts = {}
    for ach in achievements:
        ct = ach['content_type']
        type_counts[ct] = type_counts.get(ct, 0) + 1

    print("\nBy type:")
    for ct, count in sorted(type_counts.items()):
        print(f"  {ct}: {count}")

    print(f"\n✓ Saved to {output_file}")
    print("\nReview the JSON file and add missing information (faculty names, departments, dates)")
    print("Then use add_manual_achievements.py to add them to ChromaDB")


if __name__ == "__main__":
    main()
