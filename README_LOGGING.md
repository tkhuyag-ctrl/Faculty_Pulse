# Faculty Pulse - Logging Guide

## Overview
All data crawling, extraction, and database operations now have comprehensive logging to help debug issues.

## Log Files Location

All log files are stored in the `./logs/` directory with timestamped filenames:

```
Faculty_Pulse/
├── logs/
│   ├── data_extraction_20260115_143022.log
│   ├── openalex_publications.log
│   ├── pdf_extraction.log
│   ├── integration.log
│   ├── crawler.log
│   └── ...
```

## What Gets Logged

### 1. Data Extraction (`data_extractor.py`)
- **URL fetching**: Every URL fetch attempt with status
- **PDF detection**: Whether content is detected as PDF
- **PDF extraction**: Page count, characters extracted per page
- **Retry attempts**: Failed attempts and backoff delays
- **Errors**: Full error messages with context

**Log file**: `data_extraction_YYYYMMDD_HHMMSS.log`

### 2. OpenAlex Crawler (`openalex_publications_crawler.py`)
- **API requests**: OpenAlex API calls with parameters
- **Publication fetching**: Number of publications fetched per faculty
- **Database insertions**: ChromaDB add operations
- **Rate limiting**: Delays between API calls

**Log file**: `openalex_publications.log`

### 3. PDF Extraction (`download_and_extract_pdfs.py`)
- **PDF downloads**: Source of PDF (Unpaywall, arXiv, etc.)
- **PDF processing**: Success/failure of extraction
- **Cache hits**: When cached PDFs are reused
- **Database updates**: Updating ChromaDB with full text

**Log file**: `pdf_extraction.log`

### 4. Integration Script (`integrate_faculty_to_chatbot.py`)
- **Faculty processing**: Each faculty member being processed
- **Publication filtering**: Which publications are included/excluded
- **Database operations**: ChromaDB insertions
- **Summary statistics**: Total processed, success/failure counts

**Log file**: `integration.log`

### 5. Automated Crawler (`automated_crawler.py`)
- **URL tracking**: URLs added, crawl status
- **Content fetching**: Smart fetcher operations
- **Database updates**: ChromaDB operations
- **Scheduling**: Automated run information

**Log file**: `crawler.log`

## Chatbot Debugging

The chatbot (`chatbot.py`) now logs to **console output** (not file) showing:

```
############################################################
# NEW CHAT REQUEST
############################################################

============================================================
[DATABASE QUERY]
Query: Laura Been publications
n_results: 5
content_type: None
department: None

[DATABASE RESULTS]
Number of results returned: 3

Top results:
  1. ID: pub_A5049145887_W4415454151
     Faculty: Laura Been
     Department: Psychology
     Type: Publication
     Distance: 0.6580 (Relevance: 0.3420)
     Content preview: Faculty: Laura Been...

[FORMATTED RESULTS FOR CLAUDE]
Formatted results preview:
Here is the relevant information from the faculty database:

[Result 1 - Relevance: 0.34]
Faculty: Laura Been
...

[CLAUDE API CALL]
User query: Laura Been publications
Database context length: 2543 characters
Conversation history: 0 messages
Calling Claude API (model: claude-3-haiku-20240307)...

[CLAUDE RESPONSE]
Response length: 456 characters
Response preview: Based on the information in the database, Laura Been...
API usage - Input tokens: 1234, Output tokens: 89

[CHAT COMPLETE]
Returning 3 results to user
############################################################
```

## How to Use Logs for Debugging

### Problem: Can't find faculty data
**Check**: `integration.log` or `openalex_publications.log`
```bash
# Search for a specific faculty member
grep "Laura Been" logs/integration.log
grep "Laura Been" logs/openalex_publications.log
```

### Problem: PDF extraction failing
**Check**: `pdf_extraction.log` or `data_extraction_*.log`
```bash
# Find PDF extraction errors
grep "ERROR" logs/pdf_extraction.log
grep "extraction failed" logs/data_extraction_*.log
```

### Problem: Wrong PDF content (mismatch)
**Check**: `data_extraction_*.log` for URL redirects
```bash
# Look for redirects or short content warnings
grep "Warning: Extracted content is very short" logs/data_extraction_*.log
grep "redirect" logs/data_extraction_*.log
```

### Problem: Chatbot can't retrieve faculty
**Check**: Console output when running `streamlit run app.py`
- Look for "DATABASE RESULTS" section
- Check "Distance" values (should be < 0.7 for good matches)
- Verify faculty name appears in "Content preview"

### Problem: Database not updating
**Check**: `integration.log` for ChromaDB operations
```bash
grep "ChromaDB" logs/integration.log
grep "Successfully added" logs/integration.log
```

## Log Levels

- **DEBUG**: Detailed information (page-by-page extraction, etc.)
- **INFO**: General progress information (default level)
- **WARNING**: Potential issues that don't stop execution
- **ERROR**: Errors that stop processing a specific item
- **CRITICAL**: Severe errors that stop the entire process

## Enable Debug Logging

To get more detailed logs, edit the script and change:

```python
logging.basicConfig(level=logging.DEBUG, ...)
```

## Centralized Logging (New)

Use the new `logging_config.py` module for consistent logging:

```python
from logging_config import setup_crawler_logger

logger = setup_crawler_logger("my_script")
logger.info("Starting process...")
logger.error("Something failed", exc_info=True)
```

## Quick Inspection Scripts

### View all logs from today
```bash
ls -lt logs/ | head -20
```

### Search all logs for errors
```bash
grep -r "ERROR" logs/
```

### Monitor logs in real-time
```bash
tail -f logs/integration.log
```

### Count log entries by level
```bash
grep -c "INFO" logs/integration.log
grep -c "ERROR" logs/integration.log
grep -c "WARNING" logs/integration.log
```

## Best Practices

1. **Always check logs after running scripts** - Don't assume success
2. **Look for "WARNING" messages** - They indicate potential data quality issues
3. **Monitor PDF extraction** - Verify content length is reasonable (>1000 chars for papers)
4. **Check for duplicates** - Look for "already exists" messages
5. **Verify faculty names** - Ensure they match exactly what users will search for

## Troubleshooting Common Issues

### Issue: Log files growing too large
**Solution**: Logs are timestamped. Delete old log files:
```bash
# Delete logs older than 7 days
find logs/ -name "*.log" -mtime +7 -delete
```

### Issue: Can't find log file
**Solution**: Check `./logs/` directory. If missing, scripts create it automatically.

### Issue: Logs show success but database is empty
**Solution**:
1. Check `integration.log` for "Successfully added" messages
2. Run `python inspect_database.py` to verify
3. Check if ChromaDB path is correct (`./chroma_db/`)

## Summary

With comprehensive logging now in place, you can:
- ✓ Track every step of data collection
- ✓ Debug PDF extraction issues
- ✓ Verify database operations
- ✓ Monitor chatbot queries in real-time
- ✓ Identify data quality problems
- ✓ Trace errors to their source

Always run scripts with logging enabled and review the logs before adding data to the chatbot database!
