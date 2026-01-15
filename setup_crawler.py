"""
Setup and Installation Check for Automated Crawler
Run this first to verify everything is installed correctly
"""
import sys
import subprocess
import importlib.util

def check_package(package_name, import_name=None):
    """Check if a package is installed"""
    if import_name is None:
        import_name = package_name

    spec = importlib.util.find_spec(import_name)
    return spec is not None

def main():
    print("="*80)
    print("AUTOMATED CRAWLER - SETUP CHECK")
    print("="*80)

    # Check core dependencies
    print("\nChecking core dependencies...")
    core_deps = {
        'requests': 'requests',
        'beautifulsoup4': 'bs4',
        'chromadb': 'chromadb',
        'anthropic': 'anthropic',
        'streamlit': 'streamlit',
        'python-dotenv': 'dotenv'
    }

    core_ok = True
    for package, import_name in core_deps.items():
        if check_package(package, import_name):
            print(f"  [OK] {package}")
        else:
            print(f"  [MISSING] {package}")
            core_ok = False

    # Check crawler-specific dependencies
    print("\nChecking crawler dependencies...")
    crawler_deps = {
        'pypdf': 'pypdf',
        'PyMuPDF': 'fitz',
        'playwright': 'playwright',
        'schedule': 'schedule'
    }

    crawler_ok = True
    missing_crawler = []
    for package, import_name in crawler_deps.items():
        if check_package(package, import_name):
            print(f"  [OK] {package}")
        else:
            print(f"  [MISSING] {package}")
            crawler_ok = False
            missing_crawler.append(package)

    # Check if our modules can be imported
    print("\nChecking custom modules...")
    custom_modules = ['smart_fetcher', 'url_tracker', 'automated_crawler', 'scheduler']
    modules_ok = True

    for module in custom_modules:
        try:
            __import__(module)
            print(f"  [OK] {module}.py")
        except Exception as e:
            print(f"  [ERROR] {module}.py: {str(e)}")
            modules_ok = False

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    if not core_ok:
        print("\n[ERROR] Core dependencies missing!")
        print("Install with: pip install chromadb anthropic streamlit python-dotenv requests beautifulsoup4")
        return 1

    if not modules_ok:
        print("\n[ERROR] Custom modules have import errors!")
        print("Please check the error messages above.")
        return 1

    if not crawler_ok:
        print("\n[WARNING] Some crawler dependencies are missing.")
        print("\nTo install all crawler dependencies:")
        print("  pip install -r requirements_crawler.txt")

        if 'playwright' in missing_crawler:
            print("\nAfter installing Playwright, run:")
            print("  playwright install")

        print("\nYou can still use the basic features, but some functionality will be limited:")
        if 'pypdf' in missing_crawler and 'PyMuPDF' in missing_crawler:
            print("  - PDF extraction will not work")
        if 'playwright' in missing_crawler:
            print("  - Headless browser fetching will not work (will try direct/proxy only)")
        if 'schedule' in missing_crawler:
            print("  - Automated scheduling will not work")

        return 2

    print("\n[SUCCESS] All dependencies installed correctly!")
    print("\nNext steps:")
    print("1. Create a JSON file with URLs to crawl (see example_urls.json)")
    print("2. Load URLs: python automated_crawler.py load your_urls.json")
    print("3. Run crawler: python automated_crawler.py crawl")
    print("4. (Optional) Enable scheduling in crawler_config.json")
    print("\nFor detailed instructions, see CRAWLER_GUIDE.md")

    return 0

if __name__ == "__main__":
    sys.exit(main())
