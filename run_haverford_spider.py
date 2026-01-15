"""
Run spider optimized for Haverford's site structure
"""
import logging
import json
from link_spider import LinkSpider

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('haverford_spider.log')
    ]
)

print("="*80)
print("HAVERFORD FACULTY SPIDER")
print("="*80)

# Load seed URLs
with open('haverford_urls.json', 'r') as f:
    seed_data = json.load(f)

seed_urls = [entry['url'] for entry in seed_data]

print(f"\nSeed URLs:")
for url in seed_urls:
    print(f"  - {url}")

# Create spider with permissive patterns for Haverford
spider = LinkSpider(
    seed_urls=seed_urls,
    max_depth=2,
    max_urls_per_domain=100,  # Increase limit
    # More permissive patterns - include any page on haverford.edu
    allowed_patterns=[
        r'haverford\.edu/.+',  # Any page on haverford.edu with a path
        r'\.pdf$',             # PDFs
    ],
    # Exclude non-content pages
    excluded_patterns=[
        r'/calendar',
        r'/events?',
        r'/news',
        r'/apply',
        r'/admissions',
        r'/give',
        r'/donate',
        r'/login',
        r'/admin',
        r'#',
        r'\?',  # Skip URLs with query params for now
        r'\.jpg$',
        r'\.png$',
        r'\.gif$',
        r'\.css$',
        r'\.js$',
    ]
)

try:
    print(f"\nStarting discovery (max depth: 2)...")
    print("This will take several minutes...\n")

    results = spider.crawl()

    # Display stats
    spider.display_statistics()

    # Export
    output_file = "haverford_all_discovered.json"
    spider.export_to_json(output_file)

    print(f"\n{'='*80}")
    print(f"SUCCESS - Discovered {len(results)} URLs")
    print(f"Saved to: {output_file}")
    print(f"{'='*80}")

    # Show sample
    print(f"\nSample discovered URLs:")
    for i, result in enumerate(results[:10], 1):
        print(f"\n{i}. {result['url']}")
        print(f"   Dept: {result['department']}")

finally:
    spider.close()
