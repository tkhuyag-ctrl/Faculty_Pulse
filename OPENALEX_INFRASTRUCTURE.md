# OpenAlex Infrastructure for Faculty Pulse

## Summary

Yes, the infrastructure to store and produce OpenAlex IDs for Haverford faculty is already in place!

---

## Data File with OpenAlex IDs

**Main file**: [haverford_faculty_with_openalex.json](haverford_faculty_with_openalex.json)

### Statistics:
- **Total faculty**: 239
- **With OpenAlex ID**: 139 (58.2%)
- **Without OpenAlex ID**: 100 (41.8%)

### Example Entry:

```json
{
  "name": "Laura Been",
  "department": "Psychology",
  "profile_url": "https://www.haverford.edu/users/lbeen",
  "orcid": null,
  "openalex_id": "A5049145887",
  "openalex_url": "https://openalex.org/A5049145887",
  "openalex_display_name": "Laura E. Been",
  "works_count": 28,
  "cited_by_count": 245
}
```

### Department Breakdown:

| Department | With OpenAlex ID | Total | Coverage |
|------------|------------------|-------|----------|
| **Psychology** | 9 | 10 | **90%** ✅ |
| **Anthropology** | 7 | 8 | **88%** ✅ |
| **Physics** | 7 | 8 | **88%** ✅ |
| **Biology** | 13 | 16 | **81%** ✅ |
| **Computer Science** | 5 | 7 | **71%** ✅ |
| **History** | 10 | 14 | **71%** ✅ |
| **Mathematics** | 11 | 16 | **69%** ✅ |
| **Philosophy** | 6 | 9 | **67%** ✅ |
| **Sociology** | 2 | 3 | **67%** ✅ |
| **Classics** | 5 | 8 | **62%** ✅ |
| **Chemistry** | 9 | 15 | **60%** |
| **Religion** | 4 | 7 | **57%** |
| **Economics** | 6 | 11 | **55%** |
| **Political Science** | 7 | 15 | **47%** |
| **English** | 7 | 16 | **44%** |
| **Environmental Studies** | 1 | 4 | **25%** |
| **Music** | 2 | 9 | **22%** |
| **Fine Arts** | 0 | 7 | **0%** ❌ |
| **Unknown** | 28 | 56 | **50%** |

---

## Infrastructure Files

### 1. **OpenAlex ID Finder** ✅

**File**: [find_openalex_ids.py](find_openalex_ids.py)

**Purpose**: Search OpenAlex API to find author IDs for faculty

**Features**:
- Searches OpenAlex API by faculty name
- Filters results by Haverford College affiliation
- Returns OpenAlex ID, display name, works count, citations
- Handles rate limiting (429 errors)
- Comprehensive logging

**Usage**:
```bash
python find_openalex_ids.py
```

**Example function**:
```python
def search_openalex_api(faculty_name: str, affiliation: str = "Haverford College") -> Optional[Dict]:
    """
    Search for author in OpenAlex API
    Returns: Dictionary with OpenAlex ID and URL if found
    """
    # Searches OpenAlex authors API
    # Checks for Haverford College in affiliations
    # Returns match with works_count and cited_by_count
```

### 2. **CV Crawler with OpenAlex Integration** ✅

**File**: [cv_crawler_with_openalex.py](cv_crawler_with_openalex.py)

**Purpose**: Crawl faculty pages AND enrich with OpenAlex IDs

**Usage**:
```bash
python cv_crawler_with_openalex.py
```

This produces `haverford_faculty_with_openalex.json`

### 3. **OpenAlex Publications Crawler** ✅

**File**: [openalex_publications_crawler.py](openalex_publications_crawler.py)

**Purpose**: Fetch publications from OpenAlex for faculty with IDs

**Features**:
- Loads faculty from `haverford_faculty_with_openalex.json`
- Fetches all publications (2020+) for each faculty
- Stores in ChromaDB with full metadata
- Supports bulk processing

**Usage**:
```bash
python openalex_publications_crawler.py
```

**Current limitation**: Filters to Computer Science faculty only (line 46)

---

## Related Files

### Input Files:
- [haverford_all_faculty.json](haverford_all_faculty.json) - Raw faculty list
- [cs_faculty_urls.json](cs_faculty_urls.json) - CS faculty URLs

### Output Files:
- [haverford_faculty_with_openalex.json](haverford_faculty_with_openalex.json) - **Main file with OpenAlex IDs**
- [haverford_faculty_with_orcid.json](haverford_faculty_with_orcid.json) - Faculty with ORCID IDs
- [haverford_faculty_filtered_2020plus.json](haverford_faculty_filtered_2020plus.json) - Filtered dataset
- [haverford_faculty_filtered_no_history.json](haverford_faculty_filtered_no_history.json) - Another filtered dataset

---

## How to Use This Infrastructure

### Scenario 1: Add All Psychology Faculty Publications

```bash
# 1. Check which Psychology faculty have OpenAlex IDs
python check_openalex_ids.py

# Output shows: Psychology: 9/10 (90%)

# 2. Modify openalex_publications_crawler.py to include Psychology
# Edit line 46-51 to filter for Psychology:
#   cs_faculty = [
#       f for f in all_faculty
#       if f.get('department') == 'Psychology' and  # Changed from 'Computer Science'
#          f.get('openalex_id') and
#          f['openalex_id'] != 'null'
#   ]

# 3. Run the crawler
python openalex_publications_crawler.py

# This will add all Psychology faculty publications to ChromaDB
```

### Scenario 2: Add Single Faculty Publications

Use the existing script pattern:

```bash
# Copy fetch_laura_been_with_pdfs.py
cp fetch_laura_been_with_pdfs.py fetch_faculty_template.py

# Edit to change:
# - faculty_name = "John Smith"
# - department = "Biology"

python fetch_faculty_template.py
```

### Scenario 3: Add ALL Faculty with OpenAlex IDs

```python
# Modify openalex_publications_crawler.py line 46:

# OLD (CS only):
cs_faculty = [
    f for f in all_faculty
    if f.get('department') == 'Computer Science' and
       f.get('openalex_id') and
       f['openalex_id'] != 'null'
]

# NEW (ALL departments):
all_faculty_with_ids = [
    f for f in all_faculty
    if f.get('openalex_id') and
       f['openalex_id'] != 'null'
]

# Then run:
python openalex_publications_crawler.py
```

This would add publications for all **139 faculty** with OpenAlex IDs!

### Scenario 4: Find Missing OpenAlex IDs

For faculty without OpenAlex IDs, you can:

1. **Run the finder again**:
   ```bash
   python find_openalex_ids.py
   ```

2. **Manual search**:
   - Go to https://openalex.org
   - Search for faculty name + "Haverford College"
   - Copy their OpenAlex ID (e.g., A5049145887)
   - Add to JSON file manually

3. **Check why they're missing**:
   - Fine Arts faculty (0%) likely don't publish research papers
   - Music faculty (22%) may publish performances, not papers
   - Environmental Studies (25%) may be new department

---

## OpenAlex API Details

### Base URL:
```
https://api.openalex.org/
```

### Key Endpoints:

1. **Author Search**:
   ```
   GET https://api.openalex.org/authors?search=Laura%20Been
   ```

2. **Get Author Details**:
   ```
   GET https://api.openalex.org/authors/A5049145887
   ```

3. **Get Author's Works**:
   ```
   GET https://api.openalex.org/works?filter=author.id:A5049145887,publication_year:2020-
   ```

### Rate Limits:
- **100,000 requests/day** for polite pool (with email in user agent)
- **10 requests/second** maximum
- No API key required (free and open)

### Current Implementation:
- Uses polite pool: `User-Agent: mailto:research@example.com`
- Adds 0.1s delay between requests
- Handles 429 (rate limit) errors gracefully

---

## Summary

**✅ YES, the infrastructure exists!**

You have:
1. **Data file** with 139 faculty OpenAlex IDs: `haverford_faculty_with_openalex.json`
2. **Finder script** to discover new OpenAlex IDs: `find_openalex_ids.py`
3. **Crawler script** to fetch publications: `openalex_publications_crawler.py`
4. **Individual fetcher** for single faculty: `fetch_laura_been_with_pdfs.py` (template)

**Current database**: 9 publications for Laura Been only

**Next step**: Run `openalex_publications_crawler.py` to bulk-add publications for all 139 faculty with OpenAlex IDs (would add thousands of publications!)

**Estimated scale**:
- 139 faculty with OpenAlex IDs
- Average ~20 publications per faculty (2020+)
- **~2,780 publications** could be added to database

**Time estimate**: ~2-3 hours to fetch all publications (with API delays)

**Storage**: ~50-100 MB of data in ChromaDB
