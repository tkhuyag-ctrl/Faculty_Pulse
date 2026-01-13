# Changelog

## 2026-01-13 - Individual File Output

### Changed
- **Data Extractor now saves individual files**: Each extracted entry is now saved as a separate JSON file in a `data/` directory
- **File naming convention**: Files are named using the entry ID: `[id].json`
- **Command line arguments updated**:
  - Old: `python data_extractor.py input.json output.json`
  - New: `python data_extractor.py input.json [output_dir]`
- **Default output directory**: `data/` (configurable via command line)

### Benefits
- **Easier file management**: Each entry is in its own file
- **Selective loading**: Load only the files you need
- **Better organization**: Files are named by their IDs for easy identification
- **Flexible output**: Specify custom output directory as needed

### Examples

#### Extract to default data directory:
```bash
python data_extractor.py my_urls.json
# Creates: data/sub_001.json, data/sub_002.json, etc.
```

#### Extract to custom directory:
```bash
python data_extractor.py my_urls.json my_custom_dir
# Creates: my_custom_dir/sub_001.json, my_custom_dir/sub_002.json, etc.
```

#### Load entries from directory:
```python
import json
import os

entries = []
for filename in os.listdir('data'):
    if filename.endswith('.json'):
        with open(os.path.join('data', filename), 'r') as f:
            entries.append(json.load(f))
```

### Updated Files
- `data_extractor.py` - Modified to save individual files
- `example_full_workflow.py` - Updated to load from directory
- `example_individual_files.py` - New example showing individual file workflow
- `README.md` - Updated documentation
- `data_example_multiple_urls.json` - New example with multiple entries

### Migration Guide

If you have existing scripts using the old API:

**Old way:**
```python
extractor.process_json_file('input.json', 'output.json')
# Creates single file: output.json
```

**New way:**
```python
extractor.process_json_file('input.json', 'data')
# Creates multiple files: data/sub_001.json, data/sub_002.json, etc.

# Load entries:
import os
entries = []
for filename in os.listdir('data'):
    if filename.endswith('.json'):
        with open(os.path.join('data', filename), 'r') as f:
            entries.append(json.load(f))
```
