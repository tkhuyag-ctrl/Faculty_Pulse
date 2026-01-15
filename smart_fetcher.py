"""
Smart Fetcher - Intelligent web content fetching with multiple strategies
Combines direct requests, proxy rotation, and headless browser fallback
"""
import requests
import time
import random
import io
from typing import Optional, Dict, List, Tuple
from bs4 import BeautifulSoup
from enum import Enum
import logging

try:
    import pypdf
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

try:
    import fitz  # PyMuPDF
    PYMUPDF_SUPPORT = True
except ImportError:
    PYMUPDF_SUPPORT = False

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_SUPPORT = True
except ImportError:
    PLAYWRIGHT_SUPPORT = False
    print("Warning: Playwright not installed. Install with: pip install playwright && playwright install")


class FetchStrategy(Enum):
    """Enum for fetch strategies"""
    DIRECT = "direct"
    PROXY = "proxy"
    HEADLESS = "headless"
    FAILED = "failed"


class SmartFetcher:
    """
    Intelligent fetcher that tries multiple strategies to retrieve content
    """

    def __init__(
        self,
        use_proxies: bool = False,
        proxy_list: Optional[List[str]] = None,
        delay_range: Tuple[float, float] = (1.0, 3.0),
        max_retries: int = 3,
        timeout: int = 30
    ):
        """
        Initialize the smart fetcher

        Args:
            use_proxies: Whether to use proxy rotation
            proxy_list: List of proxy URLs (e.g., ["http://proxy1:8080", "http://proxy2:8080"])
            delay_range: Range for random delays between requests (min, max) in seconds
            max_retries: Maximum retry attempts per strategy
            timeout: Request timeout in seconds
        """
        self.use_proxies = use_proxies
        self.proxy_list = proxy_list or []
        self.delay_range = delay_range
        self.max_retries = max_retries
        self.timeout = timeout

        # Setup logging
        self.logger = logging.getLogger(__name__)

        # User agent rotation
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
        ]

        # Session for connection pooling
        self.session = requests.Session()
        self._update_session_headers()

        # Playwright browser (lazy loaded)
        self.playwright_browser = None
        self.playwright_context = None
        self.playwright_instance = None

    def _update_session_headers(self):
        """Update session headers with random user agent"""
        self.session.headers.update({
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        })

    def _get_random_proxy(self) -> Optional[Dict[str, str]]:
        """Get a random proxy from the proxy list"""
        if not self.proxy_list:
            return None
        proxy_url = random.choice(self.proxy_list)
        return {
            'http': proxy_url,
            'https': proxy_url
        }

    def _random_delay(self):
        """Add random delay to mimic human behavior"""
        delay = random.uniform(self.delay_range[0], self.delay_range[1])
        time.sleep(delay)

    def _extract_text_from_pdf(self, pdf_content: bytes) -> str:
        """
        Extract text from PDF content

        Args:
            pdf_content: PDF file content as bytes

        Returns:
            Extracted text from the PDF
        """
        # Try PyMuPDF first
        if PYMUPDF_SUPPORT:
            try:
                pdf_document = fitz.open(stream=pdf_content, filetype="pdf")
                text = ""
                for page_num in range(pdf_document.page_count):
                    page = pdf_document[page_num]
                    text += page.get_text()
                pdf_document.close()
                text = ' '.join(text.split())
                return text
            except Exception as e:
                self.logger.warning(f"PyMuPDF extraction failed: {str(e)}, trying pypdf...")

        # Fall back to pypdf
        if PDF_SUPPORT:
            try:
                pdf_file = io.BytesIO(pdf_content)
                pdf_reader = pypdf.PdfReader(pdf_file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text()
                text = ' '.join(text.split())
                return text
            except Exception as e:
                raise Exception(f"pypdf extraction failed: {str(e)}")

        raise Exception("No PDF extraction library available. Install pypdf or PyMuPDF.")

    def _fetch_with_requests(self, url: str, use_proxy: bool = False) -> Tuple[str, FetchStrategy]:
        """
        Fetch content using requests library

        Args:
            url: URL to fetch
            use_proxy: Whether to use proxy

        Returns:
            Tuple of (content, strategy_used)
        """
        self.logger.info(f"Attempting direct fetch: {url}")

        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    self._random_delay()
                    self._update_session_headers()  # Rotate user agent

                # Get proxy if needed
                proxies = self._get_random_proxy() if (use_proxy and self.use_proxies) else None

                response = self.session.get(
                    url,
                    timeout=self.timeout,
                    allow_redirects=True,
                    proxies=proxies
                )
                response.raise_for_status()

                # Check if it's a PDF
                content_start = response.content[:4]
                is_pdf = content_start == b'%PDF' or 'application/pdf' in response.headers.get('content-type', '').lower()

                if is_pdf:
                    self.logger.info(f"Detected PDF content, extracting text...")
                    text = self._extract_text_from_pdf(response.content)
                    strategy = FetchStrategy.PROXY if use_proxy else FetchStrategy.DIRECT
                    return text, strategy

                # Parse HTML
                soup = BeautifulSoup(response.content, 'html.parser')

                # Remove non-content elements
                for element in soup(["script", "style", "nav", "header", "footer", "aside", "iframe"]):
                    element.decompose()

                # Extract text
                text = soup.get_text()
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = ' '.join(chunk for chunk in chunks if chunk)

                if len(text) < 100:
                    raise Exception(f"Content too short ({len(text)} chars), likely blocked or redirect page")

                self.logger.info(f"Successfully fetched {len(text)} characters")
                strategy = FetchStrategy.PROXY if use_proxy else FetchStrategy.DIRECT
                return text, strategy

            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Request attempt {attempt + 1} failed: {str(e)}")
                if attempt == self.max_retries - 1:
                    raise Exception(f"All request attempts failed: {str(e)}")

    def _init_playwright(self):
        """Initialize Playwright browser (lazy loading)"""
        if not PLAYWRIGHT_SUPPORT:
            raise Exception("Playwright not installed. Install with: pip install playwright && playwright install")

        if self.playwright_browser is None:
            self.logger.info("Initializing Playwright browser...")
            self.playwright_instance = sync_playwright().start()
            self.playwright_browser = self.playwright_instance.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            self.playwright_context = self.playwright_browser.new_context(
                user_agent=random.choice(self.user_agents),
                viewport={'width': 1920, 'height': 1080},
                java_script_enabled=True
            )

    def _fetch_with_playwright(self, url: str) -> Tuple[str, FetchStrategy]:
        """
        Fetch content using Playwright headless browser

        Args:
            url: URL to fetch

        Returns:
            Tuple of (content, strategy_used)
        """
        self.logger.info(f"Attempting headless browser fetch: {url}")

        self._init_playwright()

        page = self.playwright_context.new_page()

        try:
            # Navigate to page
            page.goto(url, wait_until='networkidle', timeout=self.timeout * 1000)

            # Wait a bit for dynamic content
            page.wait_for_timeout(2000)

            # Check if it's a PDF
            content_type = page.evaluate('() => document.contentType')
            if 'pdf' in content_type.lower():
                self.logger.info("Detected PDF in browser, downloading...")
                # Get PDF content
                pdf_content = page.content()
                # For PDFs, we need to download the actual file
                response = self.session.get(url)
                text = self._extract_text_from_pdf(response.content)
                return text, FetchStrategy.HEADLESS

            # Get page content
            content = page.content()

            # Parse with BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')

            # Remove non-content elements
            for element in soup(["script", "style", "nav", "header", "footer", "aside", "iframe"]):
                element.decompose()

            # Extract text
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)

            if len(text) < 100:
                raise Exception(f"Content too short ({len(text)} chars), page may not have loaded properly")

            self.logger.info(f"Successfully fetched {len(text)} characters with headless browser")
            return text, FetchStrategy.HEADLESS

        except PlaywrightTimeoutError:
            raise Exception("Playwright timeout - page took too long to load")
        except Exception as e:
            raise Exception(f"Playwright fetch failed: {str(e)}")
        finally:
            page.close()

    def fetch(self, url: str) -> Dict:
        """
        Main fetch method - tries multiple strategies automatically

        Args:
            url: URL to fetch content from

        Returns:
            Dictionary with keys:
                - content: Extracted text content
                - strategy: Strategy that succeeded
                - error: Error message if all strategies failed
        """
        self.logger.info(f"Starting smart fetch for: {url}")

        # Strategy 1: Direct request
        try:
            content, strategy = self._fetch_with_requests(url, use_proxy=False)
            return {
                'content': content,
                'strategy': strategy.value,
                'url': url,
                'success': True
            }
        except Exception as e:
            self.logger.warning(f"Direct fetch failed: {str(e)}")

        # Strategy 2: Request with proxy rotation (if enabled)
        if self.use_proxies and self.proxy_list:
            try:
                self._random_delay()
                content, strategy = self._fetch_with_requests(url, use_proxy=True)
                return {
                    'content': content,
                    'strategy': strategy.value,
                    'url': url,
                    'success': True
                }
            except Exception as e:
                self.logger.warning(f"Proxy fetch failed: {str(e)}")

        # Strategy 3: Headless browser with Playwright
        if PLAYWRIGHT_SUPPORT:
            try:
                self._random_delay()
                content, strategy = self._fetch_with_playwright(url)
                return {
                    'content': content,
                    'strategy': strategy.value,
                    'url': url,
                    'success': True
                }
            except Exception as e:
                self.logger.warning(f"Headless browser fetch failed: {str(e)}")

        # All strategies failed
        error_msg = f"All fetch strategies failed for URL: {url}"
        self.logger.error(error_msg)
        return {
            'content': None,
            'strategy': FetchStrategy.FAILED.value,
            'url': url,
            'success': False,
            'error': error_msg
        }

    def close(self):
        """Clean up resources"""
        if self.playwright_browser:
            self.playwright_context.close()
            self.playwright_browser.close()
            self.playwright_instance.stop()
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Example usage
if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Test URLs
    test_urls = [
        "https://example.com",  # Simple page
        "https://arxiv.org/pdf/2301.00001.pdf",  # PDF
    ]

    # Initialize fetcher
    fetcher = SmartFetcher(
        use_proxies=False,  # Set to True if you have proxies
        proxy_list=[],  # Add your proxy list here
        delay_range=(1.0, 2.0)
    )

    for url in test_urls:
        print(f"\n{'='*80}")
        print(f"Testing: {url}")
        print('='*80)

        result = fetcher.fetch(url)

        if result['success']:
            print(f"✓ Success with strategy: {result['strategy']}")
            print(f"Content length: {len(result['content'])} characters")
            print(f"Preview: {result['content'][:200]}...")
        else:
            print(f"✗ Failed: {result.get('error', 'Unknown error')}")

    fetcher.close()
