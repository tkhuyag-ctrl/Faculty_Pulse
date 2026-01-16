"""
Remove all faculty that were originally marked as Unknown
"""
import json
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Load the backup (original) file to identify who was Unknown
with open('haverford_faculty_with_openalex_backup.json', 'r', encoding='utf-8') as f:
    original_data = json.load(f)

# Get list of faculty who were originally Unknown
originally_unknown = [f['name'] for f in original_data if f.get('department') == 'Unknown']

print(f"Found {len(originally_unknown)} faculty originally marked as Unknown:")
for name in originally_unknown:
    print(f"  - {name}")

# Load current data
with open('haverford_faculty_with_openalex.json', 'r', encoding='utf-8') as f:
    current_data = json.load(f)

print(f"\nOriginal database: {len(current_data)} faculty")

# Remove all originally unknown faculty
filtered_data = [f for f in current_data if f['name'] not in originally_unknown]

print(f"After removal: {len(filtered_data)} faculty")
print(f"Removed: {len(current_data) - len(filtered_data)} faculty")

# Save the filtered data
with open('haverford_faculty_with_openalex.json', 'w', encoding='utf-8') as f:
    json.dump(filtered_data, f, indent=2, ensure_ascii=False)

print(f"\n✓ Updated haverford_faculty_with_openalex.json")

# Show department breakdown after removal
dept_counts = {}
for faculty in filtered_data:
    dept = faculty.get('department', 'Unknown')
    dept_counts[dept] = dept_counts.get(dept, 0) + 1

print("\n" + "="*80)
print("DEPARTMENT BREAKDOWN AFTER REMOVAL")
print("="*80)
for dept in sorted(dept_counts.keys()):
    print(f"{dept:40} {dept_counts[dept]:3} faculty")

print(f"\nTotal: {len(filtered_data)} faculty")
