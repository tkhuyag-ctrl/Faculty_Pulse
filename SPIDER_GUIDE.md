# Link Spider - Automated URL Discovery

## What It Does

The Link Spider automatically discovers faculty-related URLs by:
1. Starting from seed URLs (like your Haverford pages)
2. Extracting all links from those pages
3. Following links that match faculty/publication patterns
4. Discovering more pages recursively
5. Extracting faculty names and departments automatically

## How It's Different from the Crawler

| Link Spider | Automated Crawler |
|-------------|-------------------|
| **Discovers** new URLs | Fetches content from **known** URLs |
| Follows links automatically | Only crawls URLs you provide |
| Finds faculty pages | Updates database with content |
| Outputs a list of URLs | Updates ChromaDB |

**Workflow:**
```
Seed URLs → Link Spider → Discovered URLs → Automated Crawler → ChromaDB
```

## Quick Start

### Step 1: Run the Spider

```bash
python link_spider.py haverford_urls.json discovered_urls.json 2
```

Parameters:
- `haverford_urls.json` - Your seed URLs (already created)
- `discovered_urls.json` - Output file with discovered URLs
- `2` - Max depth (0=seeds only, 1=one level deep, 2=two levels, etc.)

### Step 2: Review Discovered URLs

```bash
# View the discovered URLs
cat discovered_urls.json
```

### Step 3: Load into Crawler

```bash
python automated_crawler.py load discovered_urls.json
```

### Step 4: Crawl

```bash
python automated_crawler.py crawl
```

## How the Spider Works

### URL Discovery Process

```
Seed: https://www.haverford.edu/computer-science/faculty-staff
│
├─> Finds: https://www.haverford.edu/computer-science/faculty/john-doe
│   │
│   └─> Finds: https://www.haverford.edu/john-doe/publications
│       └─> Finds: https://www.haverford.edu/john-doe/paper.pdf
│
└─> Finds: https://www.haverford.edu/computer-science/faculty/jane-smith
    └─> Finds: https://www.haverford.edu/jane-smith/cv
```

### URL Filtering

The spider only follows URLs matching these patterns:
- `/faculty`
- `/staff`
- `/publications`
- `/research`
- `/people`
- `/profile`
- `/cv`
- `/bio`
- `/awards`
- `/talks`
- `/presentations`
- `.pdf` files

And excludes:
- Calendar/events
- News/blogs
- Admin/login pages
- Media files (images, CSS, JS)
- Social sharing links

### Automatic Metadata Extraction

The spider tries to extract:
- **Faculty Name** - from page titles, headers
- **Department** - from page structure
- **Content Type** - guessed from URL patterns

## Configuration

### Depth Settings

```python
# Only seed URLs (no following links)
max_depth = 0

# Seed URLs + one level of links
max_depth = 1

# Seed URLs + two levels of links (recommended)
max_depth = 2

# Deep crawling (can find a LOT of URLs)
max_depth = 3
```

### Domain Limits

By default, the spider:
- Only follows links within the same domain (haverford.edu)
- Limits to 50 URLs per domain
- Respects rate limits with 2-4 second delays

### Custom Patterns

Edit `link_spider.py` to customize:

```python
spider = LinkSpider(
    seed_urls=seed_urls,
    max_depth=2,
    max_urls_per_domain=100,  # Increase limit
    allowed_patterns=[         # Add custom patterns
        r'/faculty',
        r'/custom-page',
        # Add your patterns here
    ],
    same_domain_only=True      # Set False to follow external links
)
```

## Examples

### Example 1: Basic Discovery

```bash
# Discover URLs from Haverford
python link_spider.py haverford_urls.json discovered_urls.json 2

# Results might include:
# - https://www.haverford.edu/computer-science/faculty/professor-a
# - https://www.haverford.edu/computer-science/faculty/professor-b
# - https://scholarship.haverford.edu/publications/123
# - https://www.haverford.edu/faculty/john-doe/cv.pdf
```

### Example 2: Deep Discovery

```bash
# Go deeper (3 levels)
python link_spider.py haverford_urls.json deep_discovery.json 3
```

This will find more URLs but take longer.

### Example 3: Full Workflow

```bash
# 1. Discover URLs
python link_spider.py haverford_urls.json discovered_urls.json 2

# 2. Review what was found
python -c "import json; data = json.load(open('discovered_urls.json')); print(f'Found {len(data)} URLs')"

# 3. Load into crawler
python automated_crawler.py load discovered_urls.json

# 4. Crawl all discovered URLs
python automated_crawler.py crawl

# 5. Check results
python automated_crawler.py stats
```

### Example 4: Programmatic Usage

```python
from link_spider import LinkSpider

# Initialize spider
spider = LinkSpider(
    seed_urls=[
        "https://www.haverford.edu/computer-science/faculty-staff",
        "https://scholarship.haverford.edu/"
    ],
    max_depth=2,
    max_urls_per_domain=50
)

# Crawl
results = spider.crawl()

print(f"Discovered {len(results)} URLs")

# Export
spider.export_to_json("my_urls.json")

# Stats
spider.display_statistics()

spider.close()
```

## Statistics

After running, you'll see:

```
LINK SPIDER STATISTICS
================================================
Total URLs discovered: 47
Total URLs visited: 47

By Domain:
  www.haverford.edu: 42
  scholarship.haverford.edu: 5

By Depth:
  Depth 0: 2    (seed URLs)
  Depth 1: 15   (links from seeds)
  Depth 2: 30   (links from depth 1)

By Department:
  Computer Science: 25
  Biology: 12
  Unknown Department: 10

By Content Type:
  Publication: 35
  Award: 7
  Talk: 5
```

## Advanced Features

### Custom Faculty Detection

The spider uses heuristics to detect faculty information. You can improve accuracy by:

1. **Inspecting the HTML** of your target pages
2. **Updating the selectors** in `_extract_faculty_info()`

For example, if Haverford uses specific CSS classes:

```python
def _extract_faculty_info(self, url: str, html_content: str) -> Dict:
    soup = BeautifulSoup(html_content, 'html.parser')

    # Custom selectors for Haverford
    faculty_name = "Unknown Faculty"

    # Try Haverford-specific selector
    name_element = soup.find('div', class_='faculty-profile-name')
    if name_element:
        faculty_name = name_element.get_text(strip=True)

    # ... rest of the logic
```

### Multi-Domain Crawling

To crawl multiple universities:

```python
spider = LinkSpider(
    seed_urls=[
        "https://www.haverford.edu/faculty",
        "https://www.swarthmore.edu/faculty",
        "https://www.brynmawr.edu/faculty"
    ],
    same_domain_only=False,  # Allow cross-domain
    max_urls_per_domain=100
)
```

### Selective Link Following

To only follow specific types of pages:

```python
spider = LinkSpider(
    seed_urls=seed_urls,
    allowed_patterns=[
        r'/faculty/[^/]+$',      # Only direct faculty profile pages
        r'/publications/.*\.pdf'  # Only PDF publications
    ]
)
```

## Performance

- **Speed**: ~2-4 seconds per URL (with delays)
- **Memory**: ~100-200MB depending on depth
- **Typical Results**:
  - Depth 1: 10-30 URLs
  - Depth 2: 30-100 URLs
  - Depth 3: 100-500 URLs

## Troubleshooting

### Issue: Not finding many URLs

**Solutions:**
- Increase `max_depth`
- Increase `max_urls_per_domain`
- Add more patterns to `allowed_patterns`
- Check logs in `spider.log`

### Issue: Finding too many irrelevant URLs

**Solutions:**
- Decrease `max_depth`
- Add patterns to `excluded_patterns`
- Make `allowed_patterns` more specific

### Issue: Spider gets blocked

**Solutions:**
- Increase delays in `SmartFetcher` initialization:
```python
self.fetcher = SmartFetcher(delay_range=(3.0, 6.0))
```
- Enable proxies in the fetcher
- Reduce `max_urls_per_domain`

### Issue: Can't extract faculty names

**Cause:** Page structure differs from expected

**Solution:** Customize `_extract_faculty_info()` for your specific site structure

## Best Practices

1. **Start Small**: Use `max_depth=1` first to see what's discovered
2. **Review Before Crawling**: Check `discovered_urls.json` before loading into crawler
3. **Use Reasonable Delays**: Don't overwhelm the server
4. **Respect Robots.txt**: The spider doesn't check robots.txt automatically
5. **Be Specific**: Use targeted seed URLs (faculty pages, not homepage)

## Integration with Automated Crawler

The spider and crawler work together:

```
1. Link Spider discovers URLs
   └─> discovered_urls.json

2. Automated Crawler loads URLs
   └─> python automated_crawler.py load discovered_urls.json

3. Automated Crawler fetches content
   └─> Updates ChromaDB

4. Chatbot uses the data
   └─> Answers questions about faculty
```

## Complete Example: Haverford Faculty

```bash
# Step 1: Discover faculty URLs
echo "Discovering faculty pages..."
python link_spider.py haverford_urls.json haverford_discovered.json 2

# Step 2: Review discoveries
echo "Found URLs:"
python -c "import json; print('\n'.join([u['url'] for u in json.load(open('haverford_discovered.json'))[:10]]))"

# Step 3: Load into crawler
echo "Loading into crawler..."
python automated_crawler.py load haverford_discovered.json

# Step 4: Fetch content
echo "Crawling..."
python automated_crawler.py crawl

# Step 5: Check database
echo "Database stats:"
python automated_crawler.py stats

# Step 6: Test chatbot
echo "Starting chatbot..."
python -m streamlit run app.py
```

## Summary

The Link Spider automates URL discovery so you don't have to manually find every faculty page. It:

✅ Discovers faculty pages automatically
✅ Follows links intelligently
✅ Filters out irrelevant pages
✅ Extracts metadata automatically
✅ Outputs format compatible with crawler
✅ Respects rate limits

Combined with the Automated Crawler, you have a complete hands-free system for keeping your faculty database up-to-date!
