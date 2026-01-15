# Faculty Pulse - Automated Crawler Guide

## Overview

The automated crawler system consists of three main components:

1. **SmartFetcher** - Intelligent content fetching with multiple strategies
2. **URLTracker** - Tracks crawled URLs and prevents duplicates
3. **AutomatedCrawler** - Orchestrates everything and updates ChromaDB

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements_crawler.txt
```

### 2. Install Playwright Browsers (for headless browser support)

```bash
playwright install
```

This downloads Chromium, which is needed for websites that block regular requests.

## Quick Start

### Step 1: Add URLs to Track

Create a JSON file with URLs you want to monitor:

```json
[
  {
    "url": "https://www.haverford.edu/faculty/john-doe",
    "faculty_name": "Dr. John Doe",
    "department": "Computer Science",
    "content_type": "Publication"
  },
  {
    "url": "https://example.edu/research/paper.pdf",
    "faculty_name": "Dr. Jane Smith",
    "department": "Biology",
    "content_type": "Publication",
    "date_published": "2024-01-15T00:00:00Z"
  }
]
```

### Step 2: Load URLs into the System

```bash
python automated_crawler.py load example_urls.json
```

### Step 3: Run the Crawler

```bash
python automated_crawler.py crawl
```

This will:
- Fetch content from all pending URLs
- Try multiple strategies if blocked (direct → proxy → headless browser)
- Extract text from PDFs automatically
- Update ChromaDB with new content
- Track which URLs have been crawled

### Step 4: View Statistics

```bash
python automated_crawler.py stats
```

## How It Works

### Multi-Strategy Fetching

The `SmartFetcher` tries multiple approaches automatically:

1. **Direct Request** (fastest)
   - Uses requests library with rotating user agents
   - Works for most simple websites
   - Handles PDFs automatically

2. **Proxy Rotation** (if enabled)
   - Rotates through your proxy list
   - Bypasses IP-based blocking
   - Configure in `crawler_config.json`

3. **Headless Browser** (most powerful)
   - Uses Playwright to simulate real browser
   - Handles JavaScript-rendered content
   - Bypasses bot detection
   - Falls back automatically if other methods fail

### URL Tracking

The `URLTracker` prevents duplicate work:

- **Tracks last crawl time** - Only re-crawls after X days (configurable)
- **Content hashing** - Detects if content changed
- **Failure tracking** - Retries failed URLs with backoff
- **Status monitoring** - Success, failed, blocked, rate-limited

### Database Updates

- **Smart updates**: Only updates ChromaDB if content changed
- **Deduplication**: Uses URL-based IDs to avoid duplicates
- **Metadata preservation**: Keeps faculty name, department, content type

## Configuration

Edit `crawler_config.json`:

```json
{
  "use_proxies": false,
  "proxy_list": ["http://proxy1:8080", "http://user:pass@proxy2:8080"],
  "delay_range": [1.5, 3.0],
  "max_retries": 3,
  "timeout": 30,
  "recrawl_days": 7,
  "update_if_changed": true
}
```

### Key Settings:

- **use_proxies**: Enable proxy rotation (requires proxy_list)
- **proxy_list**: Your proxy servers (optional)
- **delay_range**: Random delay between requests [min, max] seconds
- **recrawl_days**: Days before re-checking successful URLs
- **timeout**: Request timeout in seconds

## Scheduling (Automated Updates)

### One-Time Run

```bash
python scheduler.py once
```

### Continuous Scheduling

```bash
python scheduler.py start
```

This runs in the background and crawls based on your schedule.

### Configure Schedule

Edit `crawler_config.json`:

```json
{
  "schedule": {
    "enabled": true,
    "frequency": "daily",
    "time": "02:00"
  }
}
```

Options:
- **frequency**: "daily", "weekly", or "hourly"
- **time**: "HH:MM" format (for daily/weekly)

## Advanced Usage

### Using with Proxies

If you have residential proxies (recommended for blocked sites):

```json
{
  "use_proxies": true,
  "proxy_list": [
    "http://user:pass@proxy1.provider.com:8080",
    "http://user:pass@proxy2.provider.com:8080"
  ]
}
```

Popular proxy providers:
- Bright Data
- Smartproxy
- Oxylabs
- ScraperAPI

### Handling Blocked Sites

The system automatically tries:
1. Direct request with rotating user agents
2. Request through proxy (if configured)
3. Headless browser with Playwright

If all fail, it marks the URL for retry after 24 hours.

### Monitoring Failed URLs

```python
from url_tracker import URLTracker

tracker = URLTracker()
stats = tracker.get_statistics()

print(f"Blocked URLs: {stats['blocked']}")
print(f"Failed URLs: {stats['failed']}")

# Get specific URL info
info = tracker.get_url_info("https://example.com/blocked-page")
print(f"Last error: {info['last_error']}")
```

### Manual URL Management

```python
from automated_crawler import AutomatedCrawler

crawler = AutomatedCrawler()

# Add single URL
crawler.add_faculty_url(
    url="https://example.com/new-faculty",
    faculty_name="Dr. New Professor",
    department="Physics",
    content_type="Award"
)

# Crawl specific URL
result = crawler.crawl_url("https://example.com/new-faculty")
```

## Troubleshooting

### Issue: "Playwright not installed"

**Solution:**
```bash
pip install playwright
playwright install
```

### Issue: All URLs failing with timeout

**Possible causes:**
1. Network connectivity issues
2. Website blocking all requests
3. Timeout too short for slow sites

**Solutions:**
- Increase timeout in `crawler_config.json`
- Enable proxies
- Check if Playwright is installed

### Issue: PDF extraction failing

**Solution:**
```bash
pip install PyMuPDF pypdf
```

### Issue: Content not updating in database

**Cause:** Content hasn't changed (working as designed)

**Force update:**
```python
from url_tracker import URLTracker

tracker = URLTracker()
tracker.remove_url("https://example.com/url-to-recheck")
```

Then crawl again.

## Best Practices

### 1. Respectful Crawling

- Use reasonable delays (1-3 seconds)
- Don't crawl too frequently (7+ days for re-crawls)
- Respect robots.txt
- Use appropriate User-Agent headers

### 2. Content Types

Use correct content types:
- **"Publication"** - Research papers, articles
- **"Award"** - Awards, honors, recognitions
- **"Talk"** - Presentations, lectures, talks

### 3. Monitoring

- Check logs regularly: `tail -f crawler.log`
- Review statistics: `python automated_crawler.py stats`
- Monitor failed URLs and investigate patterns

### 4. Proxy Usage

- Only use proxies if needed (blocked sites)
- Residential proxies work best
- Rotate proxies to avoid rate limits
- Test proxies before adding to config

## Integration with Chatbot

The crawler automatically updates ChromaDB, so your chatbot gets new data:

1. Crawler runs (manually or scheduled)
2. New/updated content added to ChromaDB
3. Chatbot queries updated database
4. Users see latest faculty information

No code changes needed - it just works!

## API Reference

### SmartFetcher

```python
from smart_fetcher import SmartFetcher

fetcher = SmartFetcher(
    use_proxies=False,
    proxy_list=[],
    delay_range=(1.0, 3.0),
    max_retries=3,
    timeout=30
)

result = fetcher.fetch("https://example.com")
# Returns: {'content': '...', 'strategy': 'direct', 'success': True}
```

### URLTracker

```python
from url_tracker import URLTracker

tracker = URLTracker(recrawl_days=7)

# Check if needs crawling
if tracker.needs_crawl("https://example.com"):
    # Crawl it
    pass

# Mark as crawled
tracker.mark_crawled(
    url="https://example.com",
    status=CrawlStatus.SUCCESS,
    content="...",
    strategy="direct"
)
```

### AutomatedCrawler

```python
from automated_crawler import AutomatedCrawler

crawler = AutomatedCrawler()

# Add URL
crawler.add_faculty_url(
    url="https://example.com",
    faculty_name="Dr. X",
    department="CS",
    content_type="Publication"
)

# Crawl all
results = crawler.crawl_all_pending()
```

## Example Workflow

```bash
# 1. Setup (one time)
pip install -r requirements_crawler.txt
playwright install

# 2. Configure
nano crawler_config.json  # Edit settings

# 3. Add URLs
python automated_crawler.py load faculty_urls.json

# 4. Test crawl
python automated_crawler.py crawl

# 5. Check results
python automated_crawler.py stats

# 6. Setup automation
nano crawler_config.json  # Enable scheduling
python scheduler.py start  # Run in background

# 7. Monitor
tail -f crawler.log
```

## Support

For issues or questions:
1. Check logs: `crawler.log` and `scheduler.log`
2. Review statistics: `python automated_crawler.py stats`
3. Test single URL manually with `smart_fetcher.py`

## Future Enhancements

Potential improvements:
- Email notifications for failures
- Web dashboard for monitoring
- Academic API integrations (Crossref, Semantic Scholar)
- Automatic content categorization with AI
- Support for authentication (login-protected pages)
