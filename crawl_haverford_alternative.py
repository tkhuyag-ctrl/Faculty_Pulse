"""
Alternative approach: Try different methods to access Haverford faculty data
"""
import sys
import requests
from bs4 import BeautifulSoup
import time

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

def try_method_1():
    """Try with more realistic browser headers"""
    url = "https://www.haverford.edu/academics/faculty"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0'
    }

    try:
        session = requests.Session()
        response = session.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        print("✓ Method 1 successful!")
        return response.content
    except Exception as e:
        print(f"✗ Method 1 failed: {e}")
        return None


def try_method_2():
    """Try accessing department-specific pages"""
    # List of department pages
    departments = [
        'anthropology',
        'astronomy',
        'biology',
        'chemistry',
        'classics',
        'computer-science',
        'economics',
        'english',
        'fine-arts',
        'french',
        'german',
        'history',
        'mathematics',
        'music',
        'philosophy',
        'physics',
        'political-science',
        'psychology',
        'religion',
        'sociology',
        'spanish'
    ]

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    faculty_by_dept = {}

    for dept in departments:
        url = f"https://www.haverford.edu/{dept}"
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                print(f"✓ {dept}")
                faculty_by_dept[dept] = response.content
                time.sleep(0.5)
            else:
                print(f"✗ {dept} - Status {response.status_code}")
        except Exception as e:
            print(f"✗ {dept} - {e}")

    return faculty_by_dept if faculty_by_dept else None


def main():
    print("\n" + "="*80)
    print("ALTERNATIVE HAVERFORD CRAWLING METHODS")
    print("="*80 + "\n")

    print("Method 1: Enhanced headers...")
    result1 = try_method_1()

    if result1:
        with open('haverford_faculty_page.html', 'wb') as f:
            f.write(result1)
        print("Saved to haverford_faculty_page.html")
    else:
        print("\nMethod 2: Department-specific pages...")
        result2 = try_method_2()

        if result2:
            print(f"\n✓ Successfully fetched {len(result2)} department pages")
        else:
            print("\n✗ All methods failed")
            print("\nALTERNATIVE SOLUTIONS:")
            print("1. Manually copy-paste the faculty list from the website")
            print("2. Use the Haverford API if available")
            print("3. Contact Haverford IT for data access")
            print("4. Use existing data sources (OpenAlex already has most info)")


if __name__ == "__main__":
    main()
