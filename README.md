# Faculty Pulse - ChromaDB Document Management System

A complete system for extracting text from web URLs and storing them in a ChromaDB vector database with semantic search capabilities.

## Features

✅ **Automatic ID Generation** - ChromaDB automatically generates UUIDs when IDs are not provided
✅ **Web Text Extraction** - Extract clean text content from web URLs
✅ **Vector Database Storage** - Store documents in ChromaDB with semantic search
✅ **Semantic Search** - Query documents by meaning, not just keywords
✅ **Metadata Filtering** - Filter by content type, department, etc.
✅ **Database Management** - View, clear, and manage all submissions

## Installation

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install chromadb beautifulsoup4 requests
```

## Quick Start

### 1. Extract Text from URLs

Create an input file with URLs (e.g., `my_urls.json`):
```json
[
  {
    "id": "sub_001",
    "document": "https://example.com/article",
    "metadata": {
      "faculty_name": "Dr. John Smith",
      "date_published": "2026-01-10T14:30:00Z",
      "content_type": "Award",
      "department": "Computer Science"
    }
  }
]
```

Extract text (saves individual files as `data/[id].json`):
```bash
python data_extractor.py my_urls.json
# or specify custom directory:
python data_extractor.py my_urls.json custom_output_dir
```

### 2. Add to ChromaDB

```python
from chroma_manager import ChromaDBManager
import json
import os

# Load extracted data from data directory
entries = []
for filename in os.listdir('data'):
    if filename.endswith('.json'):
        with open(os.path.join('data', filename), 'r') as f:
            entries.append(json.load(f))

# Initialize ChromaDB
manager = ChromaDBManager()

# Add entries (ID is optional - will be auto-generated if not provided)
for entry in entries:
    manager.add_single_submission(
        document=entry['document'],
        faculty_name=entry['metadata']['faculty_name'],
        date_published=entry['metadata']['date_published'],
        content_type=entry['metadata']['content_type'],
        department=entry['metadata']['department'],
        submission_id=entry.get('id')  # Optional
    )
```

### 3. Query the Database

```python
# Semantic search
results = manager.query_submissions("machine learning research", n_results=5)

# Filter by content type
results = manager.query_submissions(
    "artificial intelligence",
    content_type="Publication"
)

# Filter by department
results = manager.query_submissions(
    "teaching award",
    department="Computer Science"
)

# View all submissions
manager.display_all_submissions()
```

## File Structure

```
Faculty_Pulse/
├── chroma_manager.py           # Core ChromaDB manager class
├── data_extractor.py           # Web text extraction script
├── test_chroma_manager.py      # Comprehensive test suite
├── example_full_workflow.py    # Complete workflow demonstration
├── clear_db_demo.py            # Database clearing utility
├── DATA_EXTRACTOR_USAGE.md     # Detailed extractor documentation
├── data_example.json           # Example with text document
├── data_example_no_id.json     # Example without ID (auto-generated)
├── data_example_urls.json      # Example with URL placeholder
└── data_example_urls_real.json # Example with real Wikipedia URL
```

## Scripts

### chroma_manager.py
Core library for managing ChromaDB operations.

**Key Methods:**
- `add_single_submission()` - Add a single submission (ID optional)
- `add_submission_from_json()` - Add from JSON file
- `query_submissions()` - Semantic search with filters
- `display_all_submissions()` - View all data
- `clear_database()` - Delete all entries
- `get_collection_count()` - Get total count

**Run example:**
```bash
python chroma_manager.py
```

### data_extractor.py
Extract text content from web URLs in JSON entries. Each entry is saved as an individual file in the format `[id].json`.

**Usage:**
```bash
python data_extractor.py <input_file> [output_dir]
```

**Examples:**
```bash
# Save to default 'data' directory
python data_extractor.py data_example_urls_real.json

# Save to custom directory
python data_extractor.py data_example_urls_real.json my_output_dir
```

**Output:**
- Each entry is saved as `data/[id].json` (or `custom_dir/[id].json`)
- Example: entry with id "sub_001" → `data/sub_001.json`

**Features:**
- Saves each entry as individual JSON file
- Cleans HTML (removes scripts, styles)
- Rate limiting (configurable delay)
- Error handling (skips failed URLs)
- Progress reporting

### test_chroma_manager.py
Comprehensive test suite for ChromaDB manager.

**Run tests:**
```bash
python test_chroma_manager.py
```

**Tests:**
- ✓ Initialization
- ✓ Adding from JSON
- ✓ Adding with explicit ID
- ✓ Adding with auto-generated ID
- ✓ Collection counting
- ✓ Semantic search
- ✓ Filtered queries
- ✓ Display all submissions

### example_full_workflow.py
Demonstrates complete workflow from URLs to ChromaDB.

**Run demo:**
```bash
python example_full_workflow.py
```

**Steps:**
1. Extract text from URLs
2. Load extracted entries
3. Initialize ChromaDB
4. Add entries to database
5. Verify data
6. Query and search

### clear_db_demo.py
Utility to clear the entire database.

**Run:**
```bash
python clear_db_demo.py
```

## Content Types

Valid content types:
- `Award` - Faculty awards and recognitions
- `Publication` - Research publications
- `Talk` - Conference talks and presentations

## Metadata Structure

```json
{
  "faculty_name": "Dr. John Smith",
  "date_published": "2026-01-10T14:30:00Z",
  "content_type": "Award|Publication|Talk",
  "department": "Computer Science"
}
```

## Advanced Usage

### Programmatic Data Extraction

```python
from data_extractor import DataExtractor

extractor = DataExtractor(delay=2.0)  # 2 second delay between requests

# Process single entry
entry = {
    "id": "sub_001",
    "document": "https://example.com",
    "metadata": {...}
}
processed = extractor.process_entry(entry)
print(processed['document'])  # Extracted text
```

### Custom ChromaDB Configuration

```python
from chroma_manager import ChromaDBManager

# Custom persistence directory and collection name
manager = ChromaDBManager(
    persist_directory="./my_custom_db",
    collection_name="my_collection"
)
```

### Batch Operations

```python
# Add multiple documents at once
documents = ["doc1 text", "doc2 text", "doc3 text"]
metadatas = [{"faculty_name": "Dr. A", ...}, ...]
ids = ["id1", "id2", "id3"]  # Optional

manager.add_documents(documents, metadatas, ids)
```

## Database Location

ChromaDB stores data in: `./chroma_db/`

This directory contains the persistent vector database. You can backup or delete this folder to manage your data.

## Tips

1. **Auto-generated IDs**: Simply omit the `id` field in your JSON or pass `submission_id=None` to let ChromaDB generate UUIDs
2. **Test with small batches**: When extracting from URLs, test with 1-2 entries first
3. **Rate limiting**: Adjust delay in `DataExtractor(delay=2.0)` for slower/faster extraction
4. **Clear before testing**: Use `manager.clear_database()` for clean test runs
5. **Check extraction quality**: Review `data_extracted_output.json` before importing to ChromaDB

## Troubleshooting

**URL extraction fails:**
- Check if the URL is accessible
- Some sites block automated requests
- Try adjusting user agent in `data_extractor.py`

**Import errors:**
- Make sure virtual environment is activated: `source venv/bin/activate`
- Reinstall dependencies: `pip install chromadb beautifulsoup4 requests`

**Database issues:**
- Clear and recreate: `python clear_db_demo.py`
- Check `./chroma_db/` directory permissions

## License

MIT License

## Contributing

Contributions welcome! Please test your changes with `python test_chroma_manager.py` before submitting.
