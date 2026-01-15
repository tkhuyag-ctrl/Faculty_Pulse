"""
Automated Crawler - Main orchestration for faculty data crawling
Combines SmartFetcher, URLTracker, and ChromaDB for automated updates
"""
import logging
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

from smart_fetcher import SmartFetcher, FetchStrategy
from url_tracker import URLTracker, CrawlStatus
from chroma_manager import ChromaDBManager


class AutomatedCrawler:
    """
    Main crawler that orchestrates URL tracking, content fetching, and database updates
    """

    def __init__(
        self,
        config_file: str = "crawler_config.json",
        tracker_file: str = "url_tracker.json",
        chroma_persist_dir: str = "./chroma_db",
        log_file: Optional[str] = "crawler.log"
    ):
        """
        Initialize the automated crawler

        Args:
            config_file: Path to configuration file
            tracker_file: Path to URL tracker file
            chroma_persist_dir: ChromaDB persistence directory
            log_file: Path to log file (None to disable file logging)
        """
        # Setup logging
        self._setup_logging(log_file)
        self.logger = logging.getLogger(__name__)

        # Load configuration
        self.config = self._load_config(config_file)

        # Initialize components
        self.logger.info("Initializing crawler components...")

        self.url_tracker = URLTracker(
            tracker_file=tracker_file,
            recrawl_days=self.config.get('recrawl_days', 7)
        )

        self.fetcher = SmartFetcher(
            use_proxies=self.config.get('use_proxies', False),
            proxy_list=self.config.get('proxy_list', []),
            delay_range=tuple(self.config.get('delay_range', [1.0, 3.0])),
            max_retries=self.config.get('max_retries', 3),
            timeout=self.config.get('timeout', 30)
        )

        self.db_manager = ChromaDBManager(persist_directory=chroma_persist_dir)

        self.logger.info("Crawler initialized successfully")

    def _setup_logging(self, log_file: Optional[str]):
        """Setup logging configuration"""
        handlers = [logging.StreamHandler()]

        if log_file:
            handlers.append(logging.FileHandler(log_file))

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=handlers
        )

    def _load_config(self, config_file: str) -> Dict:
        """Load configuration from file"""
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logging.warning(f"Could not load config file: {e}. Using defaults.")

        # Return default configuration
        return {
            'use_proxies': False,
            'proxy_list': [],
            'delay_range': [1.0, 3.0],
            'max_retries': 3,
            'timeout': 30,
            'recrawl_days': 7,
            'batch_size': 10,
            'update_if_changed': True
        }

    def add_faculty_url(
        self,
        url: str,
        faculty_name: str,
        department: str,
        content_type: str = "Publication",
        metadata: Optional[Dict] = None
    ):
        """
        Add a faculty URL to track

        Args:
            url: URL to track
            faculty_name: Name of faculty member
            department: Department name
            content_type: Type of content (Award, Publication, Talk)
            metadata: Additional metadata
        """
        tracking_metadata = {
            'faculty_name': faculty_name,
            'department': department,
            'content_type': content_type
        }

        if metadata:
            tracking_metadata.update(metadata)

        self.url_tracker.add_url(url, metadata=tracking_metadata)
        self.logger.info(f"Added URL for tracking: {url}")

    def crawl_url(self, url: str) -> Dict:
        """
        Crawl a single URL and update database

        Args:
            url: URL to crawl

        Returns:
            Dictionary with crawl results
        """
        self.logger.info(f"Starting crawl for: {url}")

        # Get URL metadata
        url_info = self.url_tracker.get_url_info(url)
        if not url_info or 'metadata' not in url_info:
            self.logger.error(f"No metadata found for URL: {url}")
            return {
                'url': url,
                'success': False,
                'error': 'No metadata found'
            }

        metadata = url_info['metadata']

        # Fetch content
        fetch_result = self.fetcher.fetch(url)

        if not fetch_result['success']:
            # Mark as failed
            self.url_tracker.mark_crawled(
                url,
                CrawlStatus.FAILED,
                error=fetch_result.get('error', 'Unknown error')
            )
            self.logger.error(f"Failed to fetch {url}: {fetch_result.get('error')}")
            return fetch_result

        content = fetch_result['content']
        strategy = fetch_result['strategy']

        # Check if content has changed
        if not self.url_tracker.has_content_changed(url, content):
            self.logger.info(f"Content unchanged for {url}, skipping database update")
            self.url_tracker.mark_crawled(url, CrawlStatus.SUCCESS, content=content, strategy=strategy)
            return {
                'url': url,
                'success': True,
                'updated': False,
                'reason': 'content_unchanged'
            }

        # Add or update in database
        try:
            # Create submission ID based on URL hash
            import hashlib
            submission_id = f"url_{hashlib.md5(url.encode()).hexdigest()}"

            # Check if submission already exists
            existing = None
            try:
                all_submissions = self.db_manager.get_all_submissions()
                if submission_id in all_submissions.get('ids', []):
                    existing = submission_id
            except:
                pass

            # Get date published from URL metadata or use current time
            date_published = metadata.get('date_published', datetime.now().isoformat())

            if existing and self.config.get('update_if_changed', True):
                # Update existing submission
                self.db_manager.update_submission(
                    submission_id=submission_id,
                    document=content,
                    faculty_name=metadata['faculty_name'],
                    date_published=date_published,
                    content_type=metadata['content_type'],
                    department=metadata['department']
                )
                self.logger.info(f"Updated existing submission: {submission_id}")
            else:
                # Add new submission
                self.db_manager.add_single_submission(
                    document=content,
                    faculty_name=metadata['faculty_name'],
                    date_published=date_published,
                    content_type=metadata['content_type'],
                    department=metadata['department'],
                    submission_id=submission_id
                )
                self.logger.info(f"Added new submission: {submission_id}")

            # Mark as successfully crawled
            self.url_tracker.mark_crawled(
                url,
                CrawlStatus.SUCCESS,
                content=content,
                strategy=strategy,
                metadata={'submission_id': submission_id}
            )

            return {
                'url': url,
                'success': True,
                'updated': True,
                'submission_id': submission_id,
                'strategy': strategy
            }

        except Exception as e:
            self.logger.error(f"Database error for {url}: {str(e)}")
            self.url_tracker.mark_crawled(
                url,
                CrawlStatus.FAILED,
                error=f"Database error: {str(e)}"
            )
            return {
                'url': url,
                'success': False,
                'error': f"Database error: {str(e)}"
            }

    def crawl_all_pending(self) -> Dict:
        """
        Crawl all URLs that need crawling

        Returns:
            Dictionary with summary of crawl results
        """
        urls_to_crawl = self.url_tracker.get_urls_needing_crawl()

        self.logger.info(f"Starting batch crawl of {len(urls_to_crawl)} URLs")

        results = {
            'total': len(urls_to_crawl),
            'successful': 0,
            'failed': 0,
            'updated': 0,
            'unchanged': 0,
            'errors': []
        }

        for i, url in enumerate(urls_to_crawl, 1):
            self.logger.info(f"Crawling [{i}/{len(urls_to_crawl)}]: {url}")

            try:
                result = self.crawl_url(url)

                if result['success']:
                    results['successful'] += 1
                    if result.get('updated'):
                        results['updated'] += 1
                    else:
                        results['unchanged'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append({
                        'url': url,
                        'error': result.get('error', 'Unknown error')
                    })

            except Exception as e:
                self.logger.error(f"Unexpected error crawling {url}: {str(e)}")
                results['failed'] += 1
                results['errors'].append({
                    'url': url,
                    'error': str(e)
                })

        self.logger.info(f"Batch crawl complete: {results['successful']}/{results['total']} successful")

        return results

    def load_urls_from_json(self, json_file: str):
        """
        Load URLs from a JSON file

        Expected format:
        [
            {
                "url": "https://example.com/faculty/john-doe",
                "faculty_name": "Dr. John Doe",
                "department": "Computer Science",
                "content_type": "Publication",
                "date_published": "2024-01-01T00:00:00Z"  # Optional
            }
        ]

        Args:
            json_file: Path to JSON file
        """
        self.logger.info(f"Loading URLs from {json_file}")

        with open(json_file, 'r', encoding='utf-8') as f:
            urls_data = json.load(f)

        if not isinstance(urls_data, list):
            urls_data = [urls_data]

        for entry in urls_data:
            self.add_faculty_url(
                url=entry['url'],
                faculty_name=entry['faculty_name'],
                department=entry['department'],
                content_type=entry.get('content_type', 'Publication'),
                metadata={
                    'date_published': entry.get('date_published')
                } if 'date_published' in entry else None
            )

        self.logger.info(f"Loaded {len(urls_data)} URLs")

    def get_statistics(self) -> Dict:
        """Get comprehensive statistics"""
        return {
            'url_tracker': self.url_tracker.get_statistics(),
            'database': {
                'total_documents': self.db_manager.get_collection_count()
            }
        }

    def display_statistics(self):
        """Display statistics in readable format"""
        stats = self.get_statistics()

        print("\n" + "="*80)
        print("AUTOMATED CRAWLER STATISTICS")
        print("="*80)

        print("\nURL Tracker:")
        url_stats = stats['url_tracker']
        print(f"  Total URLs: {url_stats['total_urls']}")
        print(f"  ✓ Successful: {url_stats['successful']}")
        print(f"  ✗ Failed: {url_stats['failed']}")
        print(f"  ⊘ Blocked: {url_stats['blocked']}")
        print(f"  ↻ Needs Recrawl: {url_stats['needs_recrawl']}")

        print("\nDatabase:")
        print(f"  Total Documents: {stats['database']['total_documents']}")

        if url_stats['strategies_used']:
            print("\nFetch Strategies Used:")
            for strategy, count in url_stats['strategies_used'].items():
                print(f"  - {strategy}: {count}")

        print("="*80 + "\n")

    def close(self):
        """Clean up resources"""
        self.fetcher.close()


# Example usage and CLI interface
if __name__ == "__main__":
    import sys

    print("="*80)
    print("FACULTY PULSE - AUTOMATED CRAWLER")
    print("="*80)

    # Initialize crawler
    crawler = AutomatedCrawler()

    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python automated_crawler.py load <urls.json>    # Load URLs from JSON file")
        print("  python automated_crawler.py crawl               # Crawl all pending URLs")
        print("  python automated_crawler.py stats               # Show statistics")
        print("\nExample JSON format for loading URLs:")
        print(json.dumps([{
            "url": "https://www.haverford.edu/faculty/john-doe",
            "faculty_name": "Dr. John Doe",
            "department": "Computer Science",
            "content_type": "Publication"
        }], indent=2))
        sys.exit(0)

    command = sys.argv[1].lower()

    try:
        if command == "load":
            if len(sys.argv) < 3:
                print("Error: Please provide JSON file path")
                print("Usage: python automated_crawler.py load <urls.json>")
                sys.exit(1)

            json_file = sys.argv[2]
            crawler.load_urls_from_json(json_file)
            crawler.display_statistics()

        elif command == "crawl":
            print("\nStarting automated crawl...")
            results = crawler.crawl_all_pending()

            print("\n" + "="*80)
            print("CRAWL RESULTS")
            print("="*80)
            print(f"Total URLs: {results['total']}")
            print(f"✓ Successful: {results['successful']}")
            print(f"  - Updated: {results['updated']}")
            print(f"  - Unchanged: {results['unchanged']}")
            print(f"✗ Failed: {results['failed']}")

            if results['errors']:
                print("\nErrors:")
                for error in results['errors'][:10]:  # Show first 10 errors
                    print(f"  - {error['url']}: {error['error']}")
                if len(results['errors']) > 10:
                    print(f"  ... and {len(results['errors']) - 10} more errors")

            print("="*80)

            crawler.display_statistics()

        elif command == "stats":
            crawler.display_statistics()

        else:
            print(f"Unknown command: {command}")
            print("Available commands: load, crawl, stats")
            sys.exit(1)

    finally:
        crawler.close()
