"""
Test script for the automated crawler system
Tests SmartFetcher, URLTracker, and AutomatedCrawler integration
"""
import os
import sys
import logging
from smart_fetcher import SmartFetcher
from url_tracker import URLTracker, CrawlStatus
from automated_crawler import AutomatedCrawler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_smart_fetcher():
    """Test the SmartFetcher with a simple URL"""
    print("\n" + "="*80)
    print("TEST 1: SmartFetcher")
    print("="*80)

    fetcher = SmartFetcher(delay_range=(0.5, 1.0))

    # Test with a simple, accessible URL
    test_url = "https://example.com"
    print(f"\nFetching: {test_url}")

    result = fetcher.fetch(test_url)

    if result['success']:
        print(f"✓ Success!")
        print(f"  Strategy: {result['strategy']}")
        print(f"  Content length: {len(result['content'])} characters")
        print(f"  Preview: {result['content'][:150]}...")
        return True
    else:
        print(f"✗ Failed: {result.get('error')}")
        return False

    fetcher.close()


def test_url_tracker():
    """Test the URLTracker"""
    print("\n" + "="*80)
    print("TEST 2: URLTracker")
    print("="*80)

    # Use a test file
    tracker = URLTracker(tracker_file="test_url_tracker.json", recrawl_days=7)

    test_url = "https://example.com/test"

    # Add URL
    print(f"\nAdding URL: {test_url}")
    tracker.add_url(test_url, metadata={"faculty_name": "Test User", "department": "Test Dept"})

    # Check if needs crawl
    needs_crawl = tracker.needs_crawl(test_url)
    print(f"Needs crawl: {needs_crawl}")

    if not needs_crawl:
        print("✗ URL should need crawling (new URL)")
        return False

    # Mark as crawled
    print("Marking as successfully crawled...")
    tracker.mark_crawled(
        test_url,
        CrawlStatus.SUCCESS,
        content="Test content",
        strategy="direct"
    )

    # Check again
    needs_crawl = tracker.needs_crawl(test_url)
    print(f"Needs crawl after success: {needs_crawl}")

    if needs_crawl:
        print("✗ URL should not need crawling (just crawled)")
        return False

    # Get stats
    stats = tracker.get_statistics()
    print(f"\nStatistics:")
    print(f"  Total URLs: {stats['total_urls']}")
    print(f"  Successful: {stats['successful']}")

    # Cleanup
    if os.path.exists("test_url_tracker.json"):
        os.remove("test_url_tracker.json")

    print("✓ URLTracker test passed!")
    return True


def test_automated_crawler():
    """Test the AutomatedCrawler with a simple example"""
    print("\n" + "="*80)
    print("TEST 3: AutomatedCrawler Integration")
    print("="*80)

    # Use test database directory
    test_db_dir = "./test_chroma_db"

    crawler = AutomatedCrawler(
        tracker_file="test_crawler_tracker.json",
        chroma_persist_dir=test_db_dir
    )

    # Add a simple URL
    test_url = "https://example.com"
    print(f"\nAdding URL: {test_url}")

    crawler.add_faculty_url(
        url=test_url,
        faculty_name="Test Faculty",
        department="Test Department",
        content_type="Publication"
    )

    # Crawl it
    print("\nCrawling URL...")
    result = crawler.crawl_url(test_url)

    if result['success']:
        print(f"✓ Crawl successful!")
        print(f"  Strategy: {result.get('strategy')}")
        print(f"  Submission ID: {result.get('submission_id')}")

        # Check database
        db_count = crawler.db_manager.get_collection_count()
        print(f"  Database documents: {db_count}")

        success = True
    else:
        print(f"✗ Crawl failed: {result.get('error')}")
        success = False

    # Display stats
    print("\nCrawler Statistics:")
    crawler.display_statistics()

    # Cleanup
    crawler.close()

    if os.path.exists("test_crawler_tracker.json"):
        os.remove("test_crawler_tracker.json")

    # Cleanup test database
    import shutil
    if os.path.exists(test_db_dir):
        shutil.rmtree(test_db_dir)

    return success


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("AUTOMATED CRAWLER SYSTEM - TEST SUITE")
    print("="*80)

    tests = [
        ("SmartFetcher", test_smart_fetcher),
        ("URLTracker", test_url_tracker),
        ("AutomatedCrawler", test_automated_crawler)
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n✗ {test_name} test crashed: {str(e)}")
            import traceback
            traceback.print_exc()
            results[test_name] = False

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name}: {status}")

    all_passed = all(results.values())

    if all_passed:
        print("\n🎉 All tests passed!")
        print("\nYou're ready to use the automated crawler!")
        print("\nNext steps:")
        print("1. Install dependencies: pip install -r requirements_crawler.txt")
        print("2. Install Playwright browsers: playwright install")
        print("3. Add your URLs: python automated_crawler.py load example_urls.json")
        print("4. Run crawler: python automated_crawler.py crawl")
    else:
        print("\n⚠ Some tests failed. Please check the errors above.")
        print("\nCommon issues:")
        print("- Missing dependencies: pip install -r requirements_crawler.txt")
        print("- Playwright not installed: playwright install")
        print("- Network connectivity issues")

    print("="*80 + "\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
