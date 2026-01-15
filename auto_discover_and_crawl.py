"""
Auto Discover and Crawl - Combined spider and crawler workflow
Discovers URLs and crawls them in one go
"""
import sys
import json
import logging
from link_spider import LinkSpider
from automated_crawler import AutomatedCrawler


def discover_and_crawl(
    seed_urls_file: str,
    max_depth: int = 2,
    crawl_discovered: bool = True,
    discovered_output: str = "auto_discovered_urls.json"
):
    """
    Complete workflow: discover URLs and optionally crawl them

    Args:
        seed_urls_file: JSON file with seed URLs
        max_depth: Maximum depth for link discovery
        crawl_discovered: Whether to crawl discovered URLs immediately
        discovered_output: File to save discovered URLs
    """
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('auto_discover_crawl.log')
        ]
    )

    logger = logging.getLogger(__name__)

    print("="*80)
    print("AUTO DISCOVER AND CRAWL")
    print("="*80)

    # PHASE 1: DISCOVER URLS
    print("\n" + "="*80)
    print("PHASE 1: URL DISCOVERY")
    print("="*80)

    # Load seed URLs
    logger.info(f"Loading seed URLs from {seed_urls_file}")
    with open(seed_urls_file, 'r', encoding='utf-8') as f:
        seed_data = json.load(f)

    if isinstance(seed_data, list):
        seed_urls = [entry['url'] for entry in seed_data]
    else:
        seed_urls = [seed_data['url']]

    print(f"\nSeed URLs ({len(seed_urls)}):")
    for url in seed_urls:
        print(f"  - {url}")

    # Initialize spider
    logger.info("Initializing Link Spider...")
    spider = LinkSpider(
        seed_urls=seed_urls,
        max_depth=max_depth,
        max_urls_per_domain=50
    )

    try:
        # Discover URLs
        print(f"\nDiscovering URLs (max depth: {max_depth})...")
        print("This may take a few minutes...\n")

        results = spider.crawl()

        # Display statistics
        spider.display_statistics()

        # Export discovered URLs
        logger.info(f"Exporting discovered URLs to {discovered_output}")
        spider.export_to_json(discovered_output)

        print(f"\n✓ Discovery complete!")
        print(f"  Discovered: {len(results)} URLs")
        print(f"  Saved to: {discovered_output}")

        discovered_count = len(results)

    finally:
        spider.close()

    # PHASE 2: CRAWL DISCOVERED URLS
    if crawl_discovered and discovered_count > 0:
        print("\n" + "="*80)
        print("PHASE 2: CONTENT CRAWLING")
        print("="*80)

        print(f"\nInitializing Automated Crawler...")
        crawler = AutomatedCrawler()

        try:
            # Load discovered URLs
            print(f"Loading {discovered_count} discovered URLs...")
            crawler.load_urls_from_json(discovered_output)

            # Crawl all
            print("\nCrawling all URLs...")
            print("This may take several minutes...\n")

            crawl_results = crawler.crawl_all_pending()

            # Display results
            print("\n" + "="*80)
            print("CRAWL RESULTS")
            print("="*80)
            print(f"Total URLs: {crawl_results['total']}")
            print(f"✓ Successful: {crawl_results['successful']}")
            print(f"  - Updated: {crawl_results['updated']}")
            print(f"  - Unchanged: {crawl_results['unchanged']}")
            print(f"✗ Failed: {crawl_results['failed']}")

            if crawl_results['errors']:
                print(f"\nErrors (showing first 5):")
                for error in crawl_results['errors'][:5]:
                    print(f"  - {error['url']}")
                    print(f"    Error: {error['error']}")

            # Display final statistics
            print("\n" + "="*80)
            print("FINAL STATISTICS")
            print("="*80)
            crawler.display_statistics()

            print("\n✓ Complete workflow finished successfully!")
            print("\nNext step:")
            print("  python -m streamlit run app.py  # Start the chatbot")

        finally:
            crawler.close()

    elif not crawl_discovered:
        print("\nSkipping crawl phase (as requested)")
        print("\nTo crawl later:")
        print(f"  python automated_crawler.py load {discovered_output}")
        print(f"  python automated_crawler.py crawl")

    else:
        print("\nNo URLs discovered, nothing to crawl")


if __name__ == "__main__":
    print("="*80)
    print("FACULTY PULSE - AUTO DISCOVER AND CRAWL")
    print("="*80)

    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python auto_discover_and_crawl.py <seed_urls.json> [max_depth] [--discover-only]")
        print("\nExamples:")
        print("  # Discover and crawl (depth 2)")
        print("  python auto_discover_and_crawl.py haverford_urls.json 2")
        print()
        print("  # Only discover URLs, don't crawl yet")
        print("  python auto_discover_and_crawl.py haverford_urls.json 2 --discover-only")
        print()
        print("  # Quick discovery (depth 1)")
        print("  python auto_discover_and_crawl.py haverford_urls.json 1")
        print()
        print("Seed URLs JSON format:")
        print(json.dumps([{
            "url": "https://www.haverford.edu/computer-science/faculty-staff"
        }], indent=2))
        sys.exit(0)

    seed_file = sys.argv[1]
    max_depth = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    discover_only = '--discover-only' in sys.argv

    try:
        discover_and_crawl(
            seed_urls_file=seed_file,
            max_depth=max_depth,
            crawl_discovered=not discover_only
        )
    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
