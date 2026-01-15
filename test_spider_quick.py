"""
Quick test of the improved spider
"""
import logging
from link_spider import LinkSpider

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

print("="*80)
print("TESTING IMPROVED SPIDER")
print("="*80)

# Test with a simple URL first
test_urls = ["https://www.haverford.edu/computer-science/faculty-staff"]

print(f"\nTesting with: {test_urls[0]}")
print("Max depth: 1 (just to test fetching and link extraction)")

spider = LinkSpider(
    seed_urls=test_urls,
    max_depth=1,
    max_urls_per_domain=10  # Limit for testing
)

try:
    results = spider.crawl()

    print(f"\n{'='*80}")
    print("RESULTS")
    print('='*80)
    print(f"Total discovered: {len(results)}")

    print("\nFirst 5 URLs:")
    for i, result in enumerate(results[:5], 1):
        print(f"\n{i}. {result['url']}")
        print(f"   Faculty: {result['faculty_name']}")
        print(f"   Department: {result['department']}")
        print(f"   Depth: {result['depth']}")

    spider.display_statistics()

except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()

finally:
    spider.close()

print("\nTest complete!")
