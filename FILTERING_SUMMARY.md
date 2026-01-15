# Data Filtering Summary: Haverford Faculty (2020+ Research)

## Overview
Successfully filtered Haverford faculty dataset to include only faculty with OpenAlex IDs and their publications from 2020 onwards.

## Filtering Results

### Faculty Removal
- **Original Faculty Count:** 239
- **Removed (No OpenAlex ID):** 100 faculty
- **Retained (With OpenAlex ID):** 139 faculty

### Publication Data (2020+)
- **Faculty with Recent Publications:** 53 (38% of retained faculty)
- **Total Publications (2020+):** 278
- **Average Publications per Active Faculty:** 5.2

## Data Structure

Each faculty entry now includes:

```json
{
  "name": "Faculty Name",
  "department": "Department",
  "profile_url": "https://www.haverford.edu/users/...",
  "orcid": null,
  "openalex_id": "A5051964527",
  "openalex_url": "https://openalex.org/A5051964527",
  "openalex_display_name": "Display Name",
  "works_count": 86,
  "cited_by_count": 848,
  "publications_2020_plus": [
    {
      "id": "W4214724593",
      "title": "Publication Title",
      "publication_year": 2022,
      "publication_date": "2022-01-01",
      "doi": "https://doi.org/...",
      "type": "article",
      "cited_by_count": 0,
      "is_open_access": false,
      "primary_location": "Journal Name",
      "abstract": true
    }
  ],
  "recent_publications_count": 4
}
```

## Top 10 Most Productive Faculty (2020+)

1. **Alexander Kitroeff** (History): 30 publications
2. **Elizabeth Milićević** (Mathematics): 23 publications
3. **Bruce Partridge** (Physics): 13 publications
4. **Casey Londergan** (Chemistry): 11 publications
5. **Geoffrey Hutinet** (Biology): 11 publications
6. **Joshua Sabloff** (Mathematics): 10 publications
7. **Barak Mendelsohn** (Political Science): 9 publications
8. **Kristen Whalen** (Biology): 9 publications
9. **Ariana Huberman**: 8 publications
10. **Reginald McGee** (Mathematics): 8 publications

## Output Files

### Primary Output
**File:** `haverford_faculty_filtered_2020plus.json` (186KB)
- Contains 139 faculty members with OpenAlex IDs
- Includes full publication details for all 2020+ research
- Ready for database integration

### Original Files (Kept for Reference)
- `haverford_faculty_with_openalex.json` - Original unfiltered data (77KB)
- `haverford_faculty_with_orcid.json` - Initial extraction with ORCIDs

## What Was Removed

### 1. Faculty Without OpenAlex IDs (100 removed)
These faculty members did not have identifiable research profiles in OpenAlex, which could be due to:
- No research publications
- Research in non-indexed venues
- Name variations not matched
- Recent hires without established publication records

### 2. Pre-2020 Research
All publications before January 1, 2020 were excluded. The dataset focuses exclusively on recent research (2020-2025).

## Data Quality Notes

### API Issues Encountered
- Some faculty profiles returned errors during publication fetch
- These were logged but did not prevent data collection
- Faculty with errors have `publications_2020_plus: []` (empty array)

### Publication Coverage
- **53 faculty** (38%) have at least one publication from 2020+
- **86 faculty** (62%) have OpenAlex IDs but no recent publications indexed
  - This may indicate: inactive research, publication lag, or indexing gaps

## Integration Ready

This cleaned dataset is optimized for:
- Loading into ChromaDB for Faculty Pulse chatbot
- Research analytics and visualization
- Faculty research tracking dashboards
- Automated updates (re-run script periodically)

## How to Update

To refresh the data:

```bash
# Run the filtering and fetch script
python filter_and_fetch_recent_research.py
```

This will:
1. Load the latest faculty list
2. Filter to faculty with OpenAlex IDs
3. Fetch all publications from 2020 onwards
4. Generate updated `haverford_faculty_filtered_2020plus.json`

---

**Generated:** 2026-01-14
**Script:** `filter_and_fetch_recent_research.py`
**Source Data:** OpenAlex API (https://api.openalex.org)
