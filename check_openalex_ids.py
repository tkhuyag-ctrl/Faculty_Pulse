import json

# Load the faculty data
with open('haverford_faculty_with_openalex.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

total = len(data)
with_id = sum(1 for f in data if f.get('openalex_id') and f['openalex_id'] != 'null')
without_id = total - with_id

print(f"Total faculty: {total}")
print(f"With OpenAlex ID: {with_id} ({with_id/total*100:.1f}%)")
print(f"Without OpenAlex ID: {without_id}")

# Show breakdown by department
from collections import Counter
dept_counts = Counter()
dept_with_id = Counter()

for f in data:
    dept = f.get('department', 'Unknown')
    dept_counts[dept] += 1
    if f.get('openalex_id') and f['openalex_id'] != 'null':
        dept_with_id[dept] += 1

print("\nBreakdown by department:")
for dept in sorted(dept_counts.keys()):
    total_dept = dept_counts[dept]
    with_id_dept = dept_with_id[dept]
    pct = (with_id_dept / total_dept * 100) if total_dept > 0 else 0
    print(f"  {dept}: {with_id_dept}/{total_dept} ({pct:.0f}%)")
