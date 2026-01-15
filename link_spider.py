"""
Link Spider - Discovers and follows links from seed URLs
Automatically finds faculty pages, publications, and related content
"""
import re
import logging
from typing import List, Dict, Set, Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from smart_fetcher import SmartFetcher


class LinkSpider:
    """
    Spider that discovers and follows links from seed URLs
    """

    def __init__(
        self,
        seed_urls: List[str],
        max_depth: int = 2,
        max_urls_per_domain: int = 50,
        allowed_patterns: Optional[List[str]] = None,
        excluded_patterns: Optional[List[str]] = None,
        same_domain_only: bool = True
    ):
        """
        Initialize the link spider

        Args:
            seed_urls: Starting URLs to crawl from
            max_depth: Maximum depth to follow links (0 = seed URLs only, 1 = one level deep, etc.)
            max_urls_per_domain: Maximum URLs to discover per domain
            allowed_patterns: Regex patterns - only URLs matching these will be followed
            excluded_patterns: Regex patterns - URLs matching these will be excluded
            same_domain_only: Only follow links within the same domain as seed URLs
        """
        self.seed_urls = seed_urls
        self.max_depth = max_depth
        self.max_urls_per_domain = max_urls_per_domain
        self.same_domain_only = same_domain_only

        # Setup logging
        self.logger = logging.getLogger(__name__)

        # URL tracking
        self.discovered_urls: Set[str] = set()
        self.visited_urls: Set[str] = set()
        self.url_metadata: Dict[str, Dict] = {}

        # Domain tracking
        self.domain_counts: Dict[str, int] = {}

        # Pattern matching
        self.allowed_patterns = allowed_patterns or [
            r'/faculty',
            r'/staff',
            r'/publications?',
            r'/research',
            r'/people',
            r'/profile',
            r'/cv',
            r'/bio',
            r'/awards?',
            r'/talks?',
            r'/presentations?',
            r'\.pdf$'
        ]

        self.excluded_patterns = excluded_patterns or [
            r'/calendar',
            r'/events?',
            r'/news',
            r'/blog',
            r'/contact',
            r'/login',
            r'/admin',
            r'/wp-admin',
            r'/wp-content',
            r'/feed',
            r'/rss',
            r'\?share=',
            r'\?replytocom=',
            r'#',
            r'\.jpg$',
            r'\.png$',
            r'\.gif$',
            r'\.css$',
            r'\.js$',
            r'\.zip$',
            r'\.exe$'
        ]

        # Compile patterns for performance
        self.allowed_regex = [re.compile(p, re.IGNORECASE) for p in self.allowed_patterns]
        self.excluded_regex = [re.compile(p, re.IGNORECASE) for p in self.excluded_patterns]

        # Initialize fetcher with longer delays to avoid 403
        self.fetcher = SmartFetcher(delay_range=(3.0, 6.0), max_retries=3)

        # Cache for HTML content (needed for link extraction)
        self.html_cache: Dict[str, str] = {}

    def _normalize_url(self, url: str) -> str:
        """Normalize URL (remove fragments, trailing slashes)"""
        # Remove fragment
        if '#' in url:
            url = url.split('#')[0]

        # Remove trailing slash (except for root)
        parsed = urlparse(url)
        if parsed.path != '/':
            url = url.rstrip('/')

        return url

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL"""
        return urlparse(url).netloc

    def _is_allowed_domain(self, url: str) -> bool:
        """Check if URL is from an allowed domain"""
        if not self.same_domain_only:
            return True

        url_domain = self._get_domain(url)
        seed_domains = {self._get_domain(seed) for seed in self.seed_urls}

        return url_domain in seed_domains

    def _should_crawl_url(self, url: str, is_seed: bool = False) -> bool:
        """Determine if a URL should be crawled"""
        # Already visited
        if url in self.visited_urls:
            return False

        # Always allow seed URLs regardless of patterns
        if is_seed:
            return True

        # Check domain limits
        domain = self._get_domain(url)
        if self.domain_counts.get(domain, 0) >= self.max_urls_per_domain:
            self.logger.debug(f"Skipping {url} - domain limit reached")
            return False

        # Check if domain is allowed
        if not self._is_allowed_domain(url):
            self.logger.debug(f"Skipping {url} - not in allowed domains")
            return False

        # Check excluded patterns
        for pattern in self.excluded_regex:
            if pattern.search(url):
                self.logger.debug(f"Skipping {url} - matches excluded pattern")
                return False

        # Check allowed patterns
        matches_allowed = any(pattern.search(url) for pattern in self.allowed_regex)

        if not matches_allowed:
            self.logger.debug(f"Skipping {url} - doesn't match allowed patterns")
            return False

        return True

    def _fetch_html(self, url: str) -> Optional[str]:
        """
        Fetch raw HTML content (not just extracted text)
        Uses multi-strategy approach like SmartFetcher
        """
        try:
            import requests
            from requests.exceptions import RequestException

            # Strategy 1: Direct request with SmartFetcher's headers
            try:
                self.fetcher._update_session_headers()
                self.fetcher._random_delay()

                response = self.fetcher.session.get(url, timeout=30)
                response.raise_for_status()

                self.logger.info(f"Successfully fetched HTML via direct request")
                return response.text

            except RequestException as e:
                self.logger.warning(f"Direct HTML fetch failed: {e}")

            # Strategy 2: Headless browser with Playwright
            try:
                from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

                self.fetcher._init_playwright()
                page = self.fetcher.playwright_context.new_page()

                try:
                    self.logger.info(f"Trying headless browser for HTML...")
                    page.goto(url, wait_until='networkidle', timeout=30000)
                    page.wait_for_timeout(2000)  # Wait for dynamic content

                    # Get the full HTML
                    html_content = page.content()

                    self.logger.info(f"Successfully fetched HTML via headless browser")
                    return html_content

                finally:
                    page.close()

            except PlaywrightTimeoutError:
                self.logger.error(f"Playwright timeout for {url}")
                return None
            except Exception as e:
                self.logger.error(f"Playwright error for {url}: {e}")
                return None

        except Exception as e:
            self.logger.error(f"All HTML fetch strategies failed for {url}: {e}")
            return None

    def _extract_links(self, html_content: str, base_url: str) -> List[str]:
        """Extract all links from HTML content"""
        soup = BeautifulSoup(html_content, 'html.parser')
        links = []

        for tag in soup.find_all('a', href=True):
            href = tag['href']

            # Convert relative URLs to absolute
            absolute_url = urljoin(base_url, href)

            # Normalize
            absolute_url = self._normalize_url(absolute_url)

            # Only include HTTP(S) URLs
            if absolute_url.startswith(('http://', 'https://')):
                links.append(absolute_url)

        return links

    def _extract_faculty_info(self, url: str, html_content: str) -> Dict:
        """
        Try to extract faculty information from the page
        Uses heuristics to identify faculty names, departments, etc.
        """
        soup = BeautifulSoup(html_content, 'html.parser')

        # Try to find faculty name
        faculty_name = "Unknown Faculty"

        # Look for common faculty name patterns
        name_selectors = [
            ('h1', {}),
            ('h2', {}),
            ('.faculty-name', {}),
            ('.person-name', {}),
            ('[itemprop="name"]', {})
        ]

        for selector, attrs in name_selectors:
            if isinstance(selector, str) and selector.startswith('.'):
                # Class selector
                element = soup.find(class_=selector[1:])
            else:
                # Tag selector
                element = soup.find(selector, attrs)

            if element:
                faculty_name = element.get_text(strip=True)
                if faculty_name and len(faculty_name) < 100:  # Sanity check
                    break

        # Try to find department
        department = "Unknown Department"

        # First try URL-based extraction (most reliable for Haverford)
        # Example: https://www.haverford.edu/computer-science/faculty/john-doe
        url_parts = url.split('/')
        for i, part in enumerate(url_parts):
            # Common department indicators in URLs
            if part in ['computer-science', 'cs']:
                department = "Computer Science"
                break
            elif part in ['biology', 'bio']:
                department = "Biology"
                break
            elif part in ['mathematics', 'math']:
                department = "Mathematics"
                break
            elif part in ['physics']:
                department = "Physics"
                break
            elif part in ['chemistry', 'chem']:
                department = "Chemistry"
                break
            elif part in ['psychology', 'psych']:
                department = "Psychology"
                break
            elif part in ['economics', 'econ']:
                department = "Economics"
                break
            elif part in ['english']:
                department = "English"
                break
            elif part in ['history']:
                department = "History"
                break
            elif part in ['philosophy', 'phil']:
                department = "Philosophy"
                break
            elif part in ['political-science', 'poli-sci']:
                department = "Political Science"
                break
            # If URL contains department-like path between haverford.edu and faculty
            elif i > 0 and i < len(url_parts) - 1:
                prev_part = url_parts[i-1] if i > 0 else ""
                next_part = url_parts[i+1] if i < len(url_parts) - 1 else ""
                if 'faculty' in next_part or 'staff' in next_part:
                    # This might be a department
                    dept_candidate = part.replace('-', ' ').title()
                    if len(dept_candidate) > 3 and len(dept_candidate) < 50:
                        department = dept_candidate
                        break

        # If URL extraction failed, try HTML selectors
        if department == "Unknown Department":
            dept_selectors = [
                ('.department', {}),
                ('.faculty-department', {}),
                ('[itemprop="department"]', {}),
                ('span', {'class': 'department'}),
                ('div', {'class': 'department'}),
            ]

            for selector, attrs in dept_selectors:
                if isinstance(selector, str) and selector.startswith('.'):
                    element = soup.find(class_=selector[1:])
                else:
                    element = soup.find(selector, attrs)

                if element:
                    department = element.get_text(strip=True)
                    if department and len(department) < 100:
                        break

        # Guess content type from URL
        content_type = "Publication"  # Default

        if any(keyword in url.lower() for keyword in ['award', 'honor', 'recognition']):
            content_type = "Award"
        elif any(keyword in url.lower() for keyword in ['talk', 'presentation', 'seminar']):
            content_type = "Talk"

        return {
            'faculty_name': faculty_name,
            'department': department,
            'content_type': content_type
        }

    def crawl(self) -> List[Dict]:
        """
        Main crawl method - discovers URLs starting from seed URLs

        Returns:
            List of discovered URLs with metadata
        """
        self.logger.info(f"Starting spider with {len(self.seed_urls)} seed URLs")
        self.logger.info(f"Max depth: {self.max_depth}, Max URLs per domain: {self.max_urls_per_domain}")

        # Initialize with seed URLs at depth 0
        url_queue: List[tuple] = [(url, 0) for url in self.seed_urls]

        while url_queue:
            current_url, depth = url_queue.pop(0)

            # Normalize URL
            current_url = self._normalize_url(current_url)

            # Skip if already visited
            if current_url in self.visited_urls:
                continue

            # Skip if shouldn't crawl (mark seed URLs as special)
            is_seed = (depth == 0)
            if not self._should_crawl_url(current_url, is_seed=is_seed):
                continue

            # Mark as visited
            self.visited_urls.add(current_url)

            # Update domain count
            domain = self._get_domain(current_url)
            self.domain_counts[domain] = self.domain_counts.get(domain, 0) + 1

            self.logger.info(f"Crawling [{len(self.visited_urls)}] (depth {depth}): {current_url}")

            # Fetch HTML content
            html_content = self._fetch_html(current_url)

            if not html_content:
                self.logger.warning(f"Failed to fetch HTML from {current_url}")
                continue

            # Cache the HTML for link extraction
            self.html_cache[current_url] = html_content

            # Extract faculty info
            metadata = self._extract_faculty_info(current_url, html_content)
            metadata['depth'] = depth
            metadata['strategy'] = 'html_fetch'  # Mark that we fetched HTML

            # Store URL with metadata
            self.discovered_urls.add(current_url)
            self.url_metadata[current_url] = metadata

            self.logger.info(f"  Discovered: {metadata['faculty_name']} - {metadata['department']}")

            # Extract links if we haven't reached max depth
            if depth < self.max_depth:
                links = self._extract_links(html_content, current_url)
                self.logger.info(f"  Found {len(links)} links")

                # Add new links to queue
                for link in links:
                    if link not in self.visited_urls and link not in self.discovered_urls:
                        url_queue.append((link, depth + 1))

        self.logger.info(f"Spider completed. Discovered {len(self.discovered_urls)} URLs")

        # Return results
        results = []
        for url in self.discovered_urls:
            metadata = self.url_metadata[url]
            results.append({
                'url': url,
                'faculty_name': metadata['faculty_name'],
                'department': metadata['department'],
                'content_type': metadata['content_type'],
                'depth': metadata['depth'],
                'strategy': metadata['strategy']
            })

        return results

    def export_to_json(self, output_file: str):
        """Export discovered URLs to JSON file compatible with automated_crawler"""
        import json
        from datetime import datetime

        results = []
        for url in self.discovered_urls:
            metadata = self.url_metadata[url]
            results.append({
                'url': url,
                'faculty_name': metadata['faculty_name'],
                'department': metadata['department'],
                'content_type': metadata['content_type'],
                'date_published': datetime.now().isoformat()
            })

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Exported {len(results)} URLs to {output_file}")

    def get_statistics(self) -> Dict:
        """Get spider statistics"""
        stats = {
            'total_discovered': len(self.discovered_urls),
            'total_visited': len(self.visited_urls),
            'by_domain': self.domain_counts,
            'by_depth': {},
            'by_department': {},
            'by_content_type': {}
        }

        for url, metadata in self.url_metadata.items():
            # Count by depth
            depth = metadata['depth']
            stats['by_depth'][depth] = stats['by_depth'].get(depth, 0) + 1

            # Count by department
            dept = metadata['department']
            stats['by_department'][dept] = stats['by_department'].get(dept, 0) + 1

            # Count by content type
            content_type = metadata['content_type']
            stats['by_content_type'][content_type] = stats['by_content_type'].get(content_type, 0) + 1

        return stats

    def display_statistics(self):
        """Display spider statistics"""
        stats = self.get_statistics()

        print("\n" + "="*80)
        print("LINK SPIDER STATISTICS")
        print("="*80)
        print(f"Total URLs discovered: {stats['total_discovered']}")
        print(f"Total URLs visited: {stats['total_visited']}")

        print("\nBy Domain:")
        for domain, count in stats['by_domain'].items():
            print(f"  {domain}: {count}")

        print("\nBy Depth:")
        for depth, count in sorted(stats['by_depth'].items()):
            print(f"  Depth {depth}: {count}")

        print("\nBy Department:")
        for dept, count in stats['by_department'].items():
            print(f"  {dept}: {count}")

        print("\nBy Content Type:")
        for content_type, count in stats['by_content_type'].items():
            print(f"  {content_type}: {count}")

        print("="*80 + "\n")

    def close(self):
        """Clean up resources"""
        self.fetcher.close()


# CLI interface
if __name__ == "__main__":
    import sys
    import json

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('spider.log')
        ]
    )

    print("="*80)
    print("LINK SPIDER - AUTOMATED URL DISCOVERY")
    print("="*80)

    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python link_spider.py <seed_urls.json> [output_file.json] [max_depth]")
        print("\nExample:")
        print("  python link_spider.py haverford_urls.json discovered_urls.json 2")
        print("\nSeed URLs JSON format:")
        print(json.dumps([
            {"url": "https://www.haverford.edu/computer-science/faculty-staff"}
        ], indent=2))
        sys.exit(0)

    seed_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "discovered_urls.json"
    max_depth = int(sys.argv[3]) if len(sys.argv) > 3 else 2

    # Load seed URLs
    print(f"\nLoading seed URLs from {seed_file}...")
    with open(seed_file, 'r', encoding='utf-8') as f:
        seed_data = json.load(f)

    if isinstance(seed_data, list):
        seed_urls = [entry['url'] for entry in seed_data]
    else:
        seed_urls = [seed_data['url']]

    print(f"Loaded {len(seed_urls)} seed URLs")
    for url in seed_urls:
        print(f"  - {url}")

    # Initialize spider
    spider = LinkSpider(
        seed_urls=seed_urls,
        max_depth=max_depth,
        max_urls_per_domain=50
    )

    try:
        # Crawl
        print(f"\nStarting spider (max depth: {max_depth})...")
        results = spider.crawl()

        # Display statistics
        spider.display_statistics()

        # Export results
        print(f"\nExporting results to {output_file}...")
        spider.export_to_json(output_file)

        print(f"\n✓ Spider completed successfully!")
        print(f"  Discovered: {len(results)} URLs")
        print(f"  Saved to: {output_file}")
        print(f"\nNext step:")
        print(f"  python automated_crawler.py load {output_file}")

    finally:
        spider.close()
