# Data Extractor - Usage Guide

## Overview
The Data Extractor script extracts text content from web URLs in JSON entries and creates new JSON entries with the extracted text.

## Features
- Extracts text content from web pages
- Handles both single entries and lists of entries
- Cleans extracted text (removes scripts, styles, extra whitespace)
- Adds delay between requests to avoid overwhelming servers
- Provides detailed progress reporting
- Handles errors gracefully

## Requirements
Install dependencies:
```bash
source venv/bin/activate
pip install beautifulsoup4 requests
```

## Usage

### Command Line
```bash
python data_extractor.py <input_file> <output_file>
```

### Example
```bash
python data_extractor.py data_example_urls.json data_extracted.json
```

## Input Format

### List of Entries
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
  },
  {
    "id": "sub_002",
    "document": "https://example.com/publication",
    "metadata": {
      "faculty_name": "Dr. Jane Doe",
      "date_published": "2026-01-11T10:00:00Z",
      "content_type": "Publication",
      "department": "Physics"
    }
  }
]
```

### Single Entry
```json
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
```

## Output Format
The output has the same structure as the input, but the `document` field contains the extracted text instead of the URL.

```json
[
  {
    "id": "sub_001",
    "document": "This is the extracted text content from the web page...",
    "metadata": {
      "faculty_name": "Dr. John Smith",
      "date_published": "2026-01-10T14:30:00Z",
      "content_type": "Award",
      "department": "Computer Science"
    }
  }
]
```

## Programmatic Usage

```python
from data_extractor import DataExtractor

# Initialize extractor with 1 second delay between requests
extractor = DataExtractor(delay=1.0)

# Process a file with list of entries
extractor.process_json_file('input_urls.json', 'output_text.json')

# Or process a single entry file
extractor.process_single_entry_file('single_input.json', 'single_output.json')

# Or process a single entry directly
entry = {
    "id": "sub_001",
    "document": "https://example.com/article",
    "metadata": {...}
}
processed_entry = extractor.process_entry(entry)
print(processed_entry['document'])  # Extracted text
```

## Integration with ChromaDB Manager

After extracting text, you can directly add the entries to ChromaDB:

```python
from data_extractor import DataExtractor
from chroma_manager import ChromaDBManager
import json

# Extract text from URLs
extractor = DataExtractor()
extractor.process_json_file('input_urls.json', 'extracted_text.json')

# Load extracted entries
with open('extracted_text.json', 'r') as f:
    entries = json.load(f)

# Add to ChromaDB
manager = ChromaDBManager()
for entry in entries:
    manager.add_single_submission(
        document=entry['document'],
        faculty_name=entry['metadata']['faculty_name'],
        date_published=entry['metadata']['date_published'],
        content_type=entry['metadata']['content_type'],
        department=entry['metadata']['department'],
        submission_id=entry.get('id')  # Optional
    )

print(f"Added {len(entries)} entries to ChromaDB")
```

## Error Handling
- If a URL cannot be accessed, the entry is skipped and an error message is displayed
- The script continues processing remaining entries
- The final summary shows how many entries were successfully processed

## Configuration

### Adjust Request Delay
```python
# Increase delay to 2 seconds between requests
extractor = DataExtractor(delay=2.0)
```

### Custom Headers
Edit the `data_extractor.py` file to modify the `headers` in the `__init__` method:
```python
self.headers = {
    'User-Agent': 'Your custom user agent here'
}
```

## Tips
- Test with a small batch first before processing large lists
- Use appropriate delays to be respectful to web servers
- Check the output file to verify extracted content quality
- Some websites may block automated requests - adjust headers if needed
- For password-protected or dynamic content, you may need to modify the script

## Example Files Included
- `data_example_urls.json` - Example input with placeholder URL
- `data_example_urls_real.json` - Example input with real Wikipedia URL
- `data_extracted_real.json` - Example output with extracted Wikipedia text
