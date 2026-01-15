# Automated Publication Processing System

## Overview

Your Faculty Pulse system now automatically processes ANY new publication from ANY source through the complete pipeline:

1. **PDF Extraction** - Multi-source discovery (Unpaywall, OpenAlex, arXiv)
2. **Paywall Detection** - Labels papers as full_text, paywall, or not_found
3. **RAG Chunking** - Automatically chunks large papers (>50K words)
4. **Database Integration** - Adds to ChromaDB with full metadata

## Files Created

### 1. `auto_process_publications.py`
Main processing engine that handles individual publications or batches.

**Features:**
- Processes single publications or entire batches
- Automatic PDF extraction with fallback sources
- Intelligent paywall detection and labeling
- RAG chunking for large documents (>50K words threshold)
- Skips duplicates automatically
- Detailed logging and statistics

### 2. `watch_and_process.py`
Monitoring and scheduling system for automatic processing.

**Features:**
- Run once to process new publications
- Scheduled checks (e.g., every 24 hours)
- Directory watching for new JSON files
- State tracking (won't reprocess same files)
- Support for multiple sources

---

## Usage Examples

### Process New Publications Once

```bash
# Process all new publications from default faculty file
python auto_process_publications.py
```

This will:
- Load publications from `haverford_faculty_filtered_no_history.json`
- Extract PDFs where available
- Label with access status (full_text/paywall/not_found)
- Chunk if needed (>50K words)
- Add to ChromaDB
- Skip publications already in database

**Output:**
```
================================================================================
BATCH PROCESSING COMPLETE
================================================================================
Total: 228
Processed: 187
  - Full text: 187
  - Paywall: 30
  - Not found: 11
  - Chunked: 0
Failed: 0
================================================================================
```

---

### Watch for New Publications (Directory Monitoring)

```bash
# Watch current directory for new JSON files
python watch_and_process.py --once

# Watch specific directory
python watch_and_process.py --watch-dir ./new_publications

# Watch with custom interval (check every 30 seconds)
python watch_and_process.py --watch-dir ./new_publications --watch-interval 30
```

**Use case:** Place new JSON files in the watched directory, and they'll be automatically processed.

---

### Scheduled Automatic Processing

```bash
# Check for new publications every 24 hours
python watch_and_process.py --schedule 24

# Check every 6 hours
python watch_and_process.py --schedule 6
```

**Use case:** Run this in the background to continuously monitor for new publications from OpenAlex API or crawler results.

---

## Programmatic Usage (Python API)

### Process a Single Publication

```python
from auto_process_publications import PublicationProcessor

# Initialize processor
processor = PublicationProcessor()

# Publication data (from any source)
publication = {
    'id': 'W1234567890',
    'title': 'Research Paper Title',
    'doi': 'https://doi.org/10.1234/example',
    'publication_year': 2024,
    'is_open_access': True,
    # ... other fields
}

# Faculty info
faculty = {
    'openalex_id': 'A5049145887',
    'name': 'Dr. Jane Smith',
    'department': 'Computer Science'
}

# Process it!
processor.process_single_publication(publication, faculty)
```

### Process from Any Source

```python
from auto_process_publications import process_new_publications

# From JSON file
stats = process_new_publications('new_faculty_data.json')

# From list of publications
publications = [pub1, pub2, pub3]
faculty_info = {'name': 'Dr. Smith', 'department': 'CS', ...}
stats = process_new_publications(publications, faculty_info)

# From OpenAlex API response
import requests
response = requests.get('https://api.openalex.org/works?...')
openalex_works = response.json()['results']
stats = process_new_publications(openalex_works, faculty_info)

# From Haverford Scholarship crawler
stats = process_new_publications('haverford_discovered.json')
```

---

## Integration with Existing Systems

### OpenAlex API Integration

```python
from auto_process_publications import PublicationProcessor
import requests

processor = PublicationProcessor()

# Get recent publications from OpenAlex
def check_openalex_updates(faculty_openalex_id, since_date):
    url = f"https://api.openalex.org/works"
    params = {
        'filter': f'author.id:{faculty_openalex_id},from_publication_date:{since_date}',
        'per_page': 100
    }

    response = requests.get(url, params=params)
    new_works = response.json()['results']

    # Process each new work
    for work in new_works:
        processor.process_single_publication(work, faculty_info)

    return len(new_works)

# Check for publications since last week
import datetime
last_week = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
new_count = check_openalex_updates('A5049145887', last_week)
print(f"Processed {new_count} new publications")
```

### Crawler Integration

```python
from auto_process_publications import process_new_publications

# After your crawler runs and creates JSON output
crawler_output_file = 'haverford_discovered.json'

# Automatically process all discoveries
stats = process_new_publications(crawler_output_file)

print(f"Processed {stats['processed']} new publications")
print(f"Full text: {stats['full_text']}")
print(f"Paywalled: {stats['paywall']}")
```

### Manual Import Integration

```python
from auto_process_publications import PublicationProcessor

processor = PublicationProcessor()

# User uploads a file with publication data
uploaded_file = 'user_uploaded_publications.json'

# Process it (with error handling)
try:
    stats = processor.process_from_json_file(uploaded_file, skip_existing=True)
    print(f"Successfully imported {stats['processed']} publications")
except Exception as e:
    print(f"Error importing: {e}")
```

---

## Configuration Options

### RAG Chunking Settings

Modify chunking behavior when initializing the processor:

```python
from auto_process_publications import PublicationProcessor

processor = PublicationProcessor(
    rag_threshold_words=50000,  # Chunk documents > 50K words
    rag_chunk_size=2000,        # 2K words per chunk
    rag_overlap=200             # 200 word overlap
)
```

**When to adjust:**
- **Lower threshold** (e.g., 10000): Chunk more documents for faster retrieval
- **Larger chunks** (e.g., 5000): Keep more context in each chunk
- **More overlap** (e.g., 500): Better continuity between chunks

### Skip Existing Publications

```python
# Skip publications already in database (default)
processor.process_single_publication(pub, faculty, skip_existing=True)

# Force reprocessing (updates existing entries)
processor.process_single_publication(pub, faculty, skip_existing=False)
```

---

## Monitoring and Logs

### Log Files

- **`auto_process.log`** - Detailed processing logs
- **`watcher.log`** - Monitoring system logs
- **`pdf_extraction.log`** - PDF extraction details

### Check Processing Status

```python
from chroma_manager import ChromaDBManager

db = ChromaDBManager()

# Get all publications with access status
results = db.collection.get(include=['metadatas'])

# Count by status
from collections import Counter
statuses = [m['access_status'] for m in results['metadatas']]
print(Counter(statuses))

# Output:
# Counter({'full_text': 245, 'not_found': 62, 'paywall': 4})
```

### View Recent Additions

```python
from chroma_manager import ChromaDBManager
from datetime import datetime, timedelta

db = ChromaDBManager()

# Get publications added in last 7 days
one_week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

# Note: ChromaDB doesn't support date comparisons directly
# You'd need to track this separately or query all and filter
```

---

## Workflow Examples

### Daily Update Workflow

```bash
# 1. Run crawler to discover new publications
python automated_crawler.py

# 2. Process discoveries automatically
python auto_process_publications.py

# 3. Start chatbot with updated data
streamlit run app.py
```

### Automated Background Processing

```bash
# Start scheduled monitoring (runs forever)
python watch_and_process.py --schedule 24
```

**Runs in background, checking every 24 hours for:**
- New OpenAlex publications
- New crawler results
- New JSON files

### Manual Import Workflow

```python
from auto_process_publications import process_new_publications

# 1. Get publication data from anywhere
import requests
doi = "10.1234/example"
response = requests.get(f"https://api.openalex.org/works/doi:{doi}")
work = response.json()

# 2. Add faculty info
faculty = {
    'name': 'Dr. Smith',
    'department': 'Biology',
    'openalex_id': 'A1234567890'
}

# 3. Process it
from auto_process_publications import PublicationProcessor
processor = PublicationProcessor()
processor.process_single_publication(work, faculty)

print("Publication added to database!")
```

---

## How It Works

### Processing Pipeline

```
New Publication (from any source)
        ↓
1. Extract PDF
   ├─→ Try Unpaywall API
   ├─→ Try OpenAlex API
   └─→ Try arXiv
        ↓
2. Determine Access Status
   ├─→ PDF extracted? → full_text
   ├─→ URL found, no text? → paywall
   └─→ No URL found? → not_found
        ↓
3. Check Document Size
   └─→ > 50K words? → RAG Chunk
        ↓
4. Create Enhanced Document
   ├─→ Metadata header
   ├─→ Access status info
   └─→ Full text or unavailability notice
        ↓
5. Add to ChromaDB
   ├─→ With full metadata
   ├─→ With access_status field
   └─→ With has_full_text flag
        ↓
Done! Searchable in chatbot
```

### Access Status Determination

```python
if pdf_text extracted:
    status = 'full_text'
    # AI can read and summarize

elif pdf_url found but no text:
    status = 'paywall'
    # Behind paywall or broken link
    # AI will inform user about restriction

else:
    status = 'not_found'
    # Not in open access repositories
    # AI will explain unavailability
```

---

## Best Practices

### 1. Always Skip Existing (Unless Updating)

```python
# Normal operation - don't reprocess
stats = process_new_publications(data, skip_existing=True)

# Only force reprocessing if you've updated the extraction logic
stats = process_new_publications(data, skip_existing=False)
```

### 2. Monitor Log Files

```bash
# Watch processing in real-time
tail -f auto_process.log

# Check for errors
grep ERROR auto_process.log
```

### 3. Use Scheduled Processing for Regular Updates

```bash
# Better than manual runs
python watch_and_process.py --schedule 24

# Run as a background service (Windows)
# Create a scheduled task or use nssm.exe
```

### 4. Track Source in Metadata

Publications include a 'source' field to track origin:

```python
publication['source'] = 'openalex'
# or 'haverford_scholarship', 'manual_import', etc.
```

---

## Troubleshooting

### "Publication already exists" (but you want to update it)

```python
# Force reprocessing
processor.process_single_publication(pub, faculty, skip_existing=False)
```

### Large papers not chunking

Check the threshold:

```python
# Lower the threshold to chunk more documents
processor = PublicationProcessor(rag_threshold_words=10000)
```

### PDF extraction failing

Check logs for specific errors:

```bash
tail -100 pdf_extraction.log
```

Common issues:
- Rate limiting (wait between requests)
- Invalid PDF URLs (marked as paywall)
- Network issues (retry)

---

## Summary

Your Faculty Pulse system now has **fully automated publication processing**:

✅ **Any Source** - OpenAlex, Haverford, manual imports, crawler results
✅ **Automatic PDF Extraction** - Multi-source with intelligent fallback
✅ **Paywall Detection** - Clear labeling of access restrictions
✅ **RAG Chunking** - Automatic for large documents
✅ **Database Integration** - Seamless ChromaDB updates
✅ **Duplicate Prevention** - Skips existing publications
✅ **Monitoring** - Scheduled checks and directory watching
✅ **Logging** - Detailed processing logs

**To start automated processing:**

```bash
# One-time processing
python auto_process_publications.py

# Continuous monitoring
python watch_and_process.py --schedule 24
```

Your chatbot will automatically have access to all new publications with full text, paywall status, and chunked content as needed!
