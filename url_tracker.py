"""
URL Tracker - Manages crawled URLs and prevents duplicate processing
Tracks last crawl time, content hashes, and crawl status
"""
import json
import hashlib
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from enum import Enum


class CrawlStatus(Enum):
    """Status of URL crawl attempts"""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    BLOCKED = "blocked"
    RATE_LIMITED = "rate_limited"


class URLTracker:
    """
    Tracks URLs that have been crawled to avoid duplicates and manage updates
    """

    def __init__(self, tracker_file: str = "url_tracker.json", recrawl_days: int = 7):
        """
        Initialize the URL tracker

        Args:
            tracker_file: Path to JSON file storing tracking data
            recrawl_days: Number of days before recrawling successfully fetched URLs
        """
        self.tracker_file = tracker_file
        self.recrawl_days = recrawl_days
        self.tracking_data = self._load_tracking_data()

    def _load_tracking_data(self) -> Dict:
        """Load tracking data from file"""
        if os.path.exists(self.tracker_file):
            try:
                with open(self.tracker_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load tracking data: {e}")
                return {}
        return {}

    def _save_tracking_data(self):
        """Save tracking data to file"""
        with open(self.tracker_file, 'w', encoding='utf-8') as f:
            json.dump(self.tracking_data, f, indent=2, ensure_ascii=False)

    def _compute_content_hash(self, content: str) -> str:
        """Compute SHA256 hash of content"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def _get_url_key(self, url: str) -> str:
        """Normalize URL to use as key"""
        # Remove trailing slashes and fragments
        url = url.rstrip('/')
        if '#' in url:
            url = url.split('#')[0]
        return url

    def needs_crawl(self, url: str) -> bool:
        """
        Check if a URL needs to be crawled

        Args:
            url: URL to check

        Returns:
            True if URL should be crawled, False otherwise
        """
        url_key = self._get_url_key(url)

        # If URL not tracked, it needs crawling
        if url_key not in self.tracking_data:
            return True

        url_data = self.tracking_data[url_key]
        last_status = url_data.get('last_status')

        # If last attempt failed or was blocked, check retry logic
        if last_status in [CrawlStatus.FAILED.value, CrawlStatus.BLOCKED.value]:
            last_attempt = datetime.fromisoformat(url_data.get('last_attempt', '2000-01-01'))
            # Retry failed/blocked URLs after 1 day
            retry_after = timedelta(days=1)
            if datetime.now() - last_attempt > retry_after:
                return True
            return False

        # If rate limited, wait longer before retry
        if last_status == CrawlStatus.RATE_LIMITED.value:
            last_attempt = datetime.fromisoformat(url_data.get('last_attempt', '2000-01-01'))
            retry_after = timedelta(days=3)
            if datetime.now() - last_attempt > retry_after:
                return True
            return False

        # If previously successful, check if it's time for recrawl
        if last_status == CrawlStatus.SUCCESS.value:
            last_crawl = datetime.fromisoformat(url_data.get('last_crawl', '2000-01-01'))
            if datetime.now() - last_crawl > timedelta(days=self.recrawl_days):
                return True
            return False

        # Default: needs crawl if pending or unknown status
        return True

    def has_content_changed(self, url: str, new_content: str) -> bool:
        """
        Check if content has changed since last crawl

        Args:
            url: URL to check
            new_content: New content to compare

        Returns:
            True if content changed or URL not tracked, False if same
        """
        url_key = self._get_url_key(url)

        if url_key not in self.tracking_data:
            return True

        old_hash = self.tracking_data[url_key].get('content_hash')
        new_hash = self._compute_content_hash(new_content)

        return old_hash != new_hash

    def mark_crawled(
        self,
        url: str,
        status: CrawlStatus,
        content: Optional[str] = None,
        strategy: Optional[str] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """
        Mark a URL as crawled with status and details

        Args:
            url: URL that was crawled
            status: Crawl status
            content: Content retrieved (for computing hash)
            strategy: Fetch strategy used
            error: Error message if failed
            metadata: Additional metadata to store
        """
        url_key = self._get_url_key(url)
        now = datetime.now().isoformat()

        url_data = self.tracking_data.get(url_key, {})

        # Update basic fields
        url_data['url'] = url
        url_data['last_attempt'] = now
        url_data['last_status'] = status.value

        if status == CrawlStatus.SUCCESS:
            url_data['last_crawl'] = now
            url_data['crawl_count'] = url_data.get('crawl_count', 0) + 1

            if content:
                url_data['content_hash'] = self._compute_content_hash(content)
                url_data['content_length'] = len(content)

            if strategy:
                url_data['last_strategy'] = strategy

            # Reset failure count on success
            url_data['failure_count'] = 0

        else:
            # Increment failure count
            url_data['failure_count'] = url_data.get('failure_count', 0) + 1

            if error:
                url_data['last_error'] = error

        # Add any custom metadata
        if metadata:
            url_data['metadata'] = metadata

        self.tracking_data[url_key] = url_data
        self._save_tracking_data()

    def get_url_info(self, url: str) -> Optional[Dict]:
        """
        Get tracking information for a URL

        Args:
            url: URL to look up

        Returns:
            Dictionary with tracking info or None if not tracked
        """
        url_key = self._get_url_key(url)
        return self.tracking_data.get(url_key)

    def get_statistics(self) -> Dict:
        """
        Get statistics about tracked URLs

        Returns:
            Dictionary with statistics
        """
        stats = {
            'total_urls': len(self.tracking_data),
            'successful': 0,
            'failed': 0,
            'blocked': 0,
            'rate_limited': 0,
            'pending': 0,
            'needs_recrawl': 0,
            'strategies_used': {}
        }

        for url, data in self.tracking_data.items():
            status = data.get('last_status')

            if status == CrawlStatus.SUCCESS.value:
                stats['successful'] += 1
                strategy = data.get('last_strategy', 'unknown')
                stats['strategies_used'][strategy] = stats['strategies_used'].get(strategy, 0) + 1

                # Check if needs recrawl
                if self.needs_crawl(data['url']):
                    stats['needs_recrawl'] += 1

            elif status == CrawlStatus.FAILED.value:
                stats['failed'] += 1
            elif status == CrawlStatus.BLOCKED.value:
                stats['blocked'] += 1
            elif status == CrawlStatus.RATE_LIMITED.value:
                stats['rate_limited'] += 1
            else:
                stats['pending'] += 1

        return stats

    def get_urls_needing_crawl(self) -> List[str]:
        """
        Get list of URLs that need to be crawled

        Returns:
            List of URLs that should be crawled
        """
        urls_to_crawl = []

        for url_key, data in self.tracking_data.items():
            url = data['url']
            if self.needs_crawl(url):
                urls_to_crawl.append(url)

        return urls_to_crawl

    def add_url(self, url: str, metadata: Optional[Dict] = None):
        """
        Add a new URL to track (marks as pending)

        Args:
            url: URL to add
            metadata: Optional metadata to store with URL
        """
        url_key = self._get_url_key(url)

        if url_key not in self.tracking_data:
            self.tracking_data[url_key] = {
                'url': url,
                'last_status': CrawlStatus.PENDING.value,
                'added_date': datetime.now().isoformat(),
                'metadata': metadata or {}
            }
            self._save_tracking_data()

    def remove_url(self, url: str):
        """Remove a URL from tracking"""
        url_key = self._get_url_key(url)
        if url_key in self.tracking_data:
            del self.tracking_data[url_key]
            self._save_tracking_data()

    def display_statistics(self):
        """Print statistics in a readable format"""
        stats = self.get_statistics()

        print("\n" + "="*80)
        print("URL TRACKER STATISTICS")
        print("="*80)
        print(f"Total URLs tracked: {stats['total_urls']}")
        print(f"  ✓ Successful: {stats['successful']}")
        print(f"  ✗ Failed: {stats['failed']}")
        print(f"  ⊘ Blocked: {stats['blocked']}")
        print(f"  ⏸ Rate Limited: {stats['rate_limited']}")
        print(f"  ⋯ Pending: {stats['pending']}")
        print(f"  ↻ Needs Recrawl: {stats['needs_recrawl']}")

        if stats['strategies_used']:
            print("\nStrategies Used:")
            for strategy, count in stats['strategies_used'].items():
                print(f"  - {strategy}: {count}")

        print("="*80 + "\n")


# Example usage
if __name__ == "__main__":
    # Initialize tracker
    tracker = URLTracker(tracker_file="test_url_tracker.json", recrawl_days=7)

    # Add some test URLs
    test_urls = [
        "https://www.haverford.edu/faculty/john-doe",
        "https://www.haverford.edu/faculty/jane-smith",
        "https://example.com/blocked-page"
    ]

    print("Adding test URLs...")
    for url in test_urls:
        tracker.add_url(url, metadata={"department": "Computer Science"})

    # Simulate crawling
    print("\nSimulating crawls...")

    # Success case
    tracker.mark_crawled(
        test_urls[0],
        CrawlStatus.SUCCESS,
        content="This is test content for John Doe's faculty page.",
        strategy="direct"
    )

    # Blocked case
    tracker.mark_crawled(
        test_urls[2],
        CrawlStatus.BLOCKED,
        error="403 Forbidden"
    )

    # Display statistics
    tracker.display_statistics()

    # Check which URLs need crawling
    print("URLs needing crawl:")
    for url in tracker.get_urls_needing_crawl():
        print(f"  - {url}")

    # Check specific URL info
    print(f"\nInfo for {test_urls[0]}:")
    info = tracker.get_url_info(test_urls[0])
    print(json.dumps(info, indent=2))

    # Clean up test file
    if os.path.exists("test_url_tracker.json"):
        os.remove("test_url_tracker.json")
        print("\nTest file cleaned up.")
