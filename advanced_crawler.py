"""
Advanced web crawler with full anti-detection methods
Uses Selenium with stealth mode for JavaScript-rendered pages
"""
import sys
import requests
from bs4 import BeautifulSoup
import json
import time
import random
import re
from datetime import datetime
from urllib.parse import urlparse

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Faculty update URLs
FACULTY_UPDATE_URLS = [
    "https://www.haverford.edu/college-communications/news/winter-2025-faculty-update",
    "https://www.haverford.edu/marketing-and-communications/news/spring-2025-faculty-update",
    "https://www.haverford.edu/marketing-and-communications/news/fall-2025-faculty-update",
    "https://www.haverford.edu/college-communications/news/summer-2024-faculty-update",
    "https://www.haverford.edu/college-communications/news/fall-2024-faculty-update",
    "https://www.haverford.edu/college-communications/news/spring-2024-faculty-update",
    "https://www.haverford.edu/college-communications/news/winter-2024-faculty-update",
    "https://www.haverford.edu/college-communications/news/summer-2023-faculty-update",
    "https://www.haverford.edu/college-communications/news/spring-2023-faculty-update",
    "https://www.haverford.edu/college-communications/news/spring-faculty-updates-2022",
    "https://www.haverford.edu/college-communications/news/winter-2022-faculty-update",
]


class AdvancedCrawler:
    """Advanced web crawler with anti-detection measures"""

    def __init__(self):
        self.session = None
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]

    def get_random_headers(self, url):
        """Generate realistic browser headers"""
        parsed = urlparse(url)

        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'DNT': '1',
            'Referer': f'https://{parsed.netloc}/',
        }

    def method_1_session_with_cookies(self, url):
        """Method 1: Session with cookies and full browser simulation"""
        try:
            session = requests.Session()

            # First visit homepage to get cookies
            homepage = f"https://{urlparse(url).netloc}/"
            headers = self.get_random_headers(homepage)

            print("    → Visiting homepage first to establish session...")
            home_response = session.get(homepage, headers=headers, timeout=30)

            if home_response.status_code == 200:
                time.sleep(random.uniform(1.5, 3.0))  # Human-like delay

                # Now visit actual page
                headers = self.get_random_headers(url)
                response = session.get(url, headers=headers, timeout=30)

                if response.status_code == 200:
                    return response.content, "Method 1: Session with cookies"

        except Exception as e:
            print(f"    ✗ Method 1 error: {str(e)[:50]}")

        return None, None

    def method_2_requests_with_retry(self, url):
        """Method 2: Multiple retry attempts with different user agents"""
        for attempt in range(3):
            try:
                headers = self.get_random_headers(url)
                response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)

                if response.status_code == 200:
                    return response.content, f"Method 2: Retry attempt {attempt + 1}"

                time.sleep(random.uniform(2, 4))

            except Exception as e:
                if attempt == 2:
                    print(f"    ✗ Method 2 error: {str(e)[:50]}")
                continue

        return None, None

    def method_3_alternative_endpoints(self, url):
        """Method 3: Try alternative URL patterns"""
        alternatives = [
            url,
            url.replace('/news/', '/news-events/'),
            url + '/',
            url.rstrip('/'),
            url.replace('https://', 'http://'),
        ]

        for alt_url in alternatives:
            try:
                headers = self.get_random_headers(alt_url)
                response = requests.get(alt_url, headers=headers, timeout=20)

                if response.status_code == 200:
                    return response.content, f"Method 3: Alternative endpoint"

            except Exception as e:
                continue

        return None, None

    def method_4_mobile_user_agent(self, url):
        """Method 4: Try with mobile user agent (sometimes less restricted)"""
        mobile_agents = [
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Linux; Android 13; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
        ]

        try:
            headers = self.get_random_headers(url)
            headers['User-Agent'] = random.choice(mobile_agents)

            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code == 200:
                return response.content, "Method 4: Mobile user agent"

        except Exception as e:
            print(f"    ✗ Method 4 error: {str(e)[:50]}")

        return None, None

    def method_5_slow_request_with_delay(self, url):
        """Method 5: Slow, patient requests with long delays"""
        try:
            session = requests.Session()

            # Very slow, patient approach
            time.sleep(random.uniform(3, 5))

            headers = self.get_random_headers(url)
            response = session.get(
                url,
                headers=headers,
                timeout=60,
                stream=True  # Stream the response
            )

            if response.status_code == 200:
                content = b''
                for chunk in response.iter_content(chunk_size=8192):
                    content += chunk
                    time.sleep(0.1)  # Slow download

                return content, "Method 5: Slow patient request"

        except Exception as e:
            print(f"    ✗ Method 5 error: {str(e)[:50]}")

        return None, None

    def try_selenium_method(self, url):
        """Method 6: Use Selenium with undetected-chromedriver"""
        try:
            import undetected_chromedriver as uc
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            print("    → Attempting Selenium with anti-detection...")

            options = uc.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--no-sandbox')

            driver = uc.Chrome(options=options)

            try:
                driver.get(url)

                # Wait for page to load
                time.sleep(random.uniform(3, 5))

                # Get page source
                html = driver.page_source

                driver.quit()

                if len(html) > 1000:
                    return html.encode('utf-8'), "Method 6: Selenium undetected"

            finally:
                try:
                    driver.quit()
                except:
                    pass

        except ImportError:
            print("    ✗ Selenium not available (install: pip install undetected-chromedriver)")
        except Exception as e:
            print(f"    ✗ Selenium error: {str(e)[:50]}")

        return None, None

    def crawl_url(self, url):
        """Try all methods to crawl a URL"""
        methods = [
            self.method_1_session_with_cookies,
            self.method_2_requests_with_retry,
            self.method_4_mobile_user_agent,
            self.method_5_slow_request_with_delay,
            self.method_3_alternative_endpoints,
            self.try_selenium_method,
        ]

        for method in methods:
            content, method_name = method(url)

            if content:
                return content, method_name

            # Small delay between methods
            time.sleep(random.uniform(1, 2))

        return None, None


def extract_achievements(html_content):
    """Extract faculty achievements from HTML"""
    soup = BeautifulSoup(html_content, 'html.parser')

    achievements = []

    # Find main content area
    content = (
        soup.find('div', class_='field-item') or
        soup.find('article') or
        soup.find('main') or
        soup.find('div', class_='content')
    )

    if not content:
        return achievements

    # Extract all paragraphs
    paragraphs = content.find_all('p')

    for p in paragraphs:
        text = p.get_text(strip=True)

        if len(text) < 30:
            continue

        # Check for achievement keywords
        keywords = ['award', 'grant', 'fellowship', 'prize', 'presented', 'talk',
                   'keynote', 'published', 'book', 'received', 'won', 'named']

        if any(keyword in text.lower() for keyword in keywords):
            achievements.append(text)

    return achievements


def main():
    print("\n" + "="*80)
    print("ADVANCED CRAWLER WITH FULL ANTI-DETECTION")
    print("="*80 + "\n")

    crawler = AdvancedCrawler()

    successful = 0
    failed = 0
    all_achievements = []

    for i, url in enumerate(FACULTY_UPDATE_URLS, 1):
        print(f"\n[{i}/{len(FACULTY_UPDATE_URLS)}] {url}")

        content, method = crawler.crawl_url(url)

        if content:
            print(f"  ✓ SUCCESS with {method}")
            successful += 1

            # Extract achievements
            achievements = extract_achievements(content)
            print(f"  → Found {len(achievements)} achievements")

            all_achievements.extend(achievements)

            # Save HTML
            filename = f"faculty_update_{i}.html"
            with open(filename, 'wb') as f:
                f.write(content)
            print(f"  → Saved to {filename}")

        else:
            print(f"  ✗ FAILED - All methods exhausted")
            failed += 1

        # Polite delay between URLs
        if i < len(FACULTY_UPDATE_URLS):
            delay = random.uniform(5, 10)
            print(f"  → Waiting {delay:.1f}s before next request...")
            time.sleep(delay)

    # Summary
    print("\n" + "="*80)
    print("CRAWLING SUMMARY")
    print("="*80)
    print(f"\nSuccessful: {successful}/{len(FACULTY_UPDATE_URLS)}")
    print(f"Failed: {failed}/{len(FACULTY_UPDATE_URLS)}")
    print(f"Total achievements found: {len(all_achievements)}")

    # Save achievements
    with open('achievements_extracted.json', 'w', encoding='utf-8') as f:
        json.dump(all_achievements, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Saved to achievements_extracted.json")

    # Show samples
    if all_achievements:
        print("\n" + "="*80)
        print("SAMPLE ACHIEVEMENTS")
        print("="*80)
        for achievement in all_achievements[:5]:
            print(f"\n  {achievement[:150]}...")


if __name__ == "__main__":
    main()
