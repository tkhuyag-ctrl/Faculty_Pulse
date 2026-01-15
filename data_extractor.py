"""
Data Extractor Script
Extracts text content from web links in JSON entries and creates new entries with text content
"""
import json
import requests
from bs4 import BeautifulSoup
from typing import List, Dict
import time
import os
import io
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'data_extraction_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

try:
    import pypdf
    PDF_SUPPORT = True
    logger.info("pypdf library loaded successfully")
except ImportError:
    PDF_SUPPORT = False
    logger.warning("pypdf not installed. PDF extraction will not be available.")

try:
    import fitz  # PyMuPDF
    PYMUPDF_SUPPORT = True
    logger.info("PyMuPDF library loaded successfully")
except ImportError:
    PYMUPDF_SUPPORT = False
    logger.warning("PyMuPDF not installed. Falling back to pypdf for PDF extraction.")


class DataExtractor:
    """Extracts text content from web URLs in JSON entries"""

    def __init__(self, delay: float = 1.0, max_retries: int = 3):
        """
        Initialize the data extractor

        Args:
            delay: Delay in seconds between requests to avoid overwhelming servers
            max_retries: Maximum number of retry attempts for failed requests
        """
        logger.info(f"Initializing DataExtractor (delay={delay}s, max_retries={max_retries})")
        self.delay = delay
        self.max_retries = max_retries
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
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
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def extract_text_from_pdf(self, pdf_content: bytes) -> str:
        """
        Extract text from PDF content

        Args:
            pdf_content: PDF file content as bytes

        Returns:
            Extracted text from the PDF

        Raises:
            Exception: If PDF extraction fails
        """
        logger.info(f"Starting PDF extraction (size: {len(pdf_content)} bytes)")

        # Try PyMuPDF first (generally better extraction quality)
        if PYMUPDF_SUPPORT:
            try:
                logger.debug("Attempting PyMuPDF extraction")
                pdf_document = fitz.open(stream=pdf_content, filetype="pdf")
                page_count = pdf_document.page_count
                logger.info(f"PDF has {page_count} pages")

                text = ""
                for page_num in range(page_count):
                    page = pdf_document[page_num]
                    page_text = page.get_text()
                    text += page_text
                    logger.debug(f"Extracted {len(page_text)} chars from page {page_num + 1}/{page_count}")
                pdf_document.close()

                # Clean up text
                text = ' '.join(text.split())
                logger.info(f"PyMuPDF extraction successful: {len(text)} characters extracted")
                return text
            except Exception as e:
                logger.warning(f"PyMuPDF extraction failed: {str(e)}, trying pypdf...")

        # Fall back to pypdf
        if PDF_SUPPORT:
            try:
                logger.debug("Attempting pypdf extraction")
                pdf_file = io.BytesIO(pdf_content)
                pdf_reader = pypdf.PdfReader(pdf_file)
                page_count = len(pdf_reader.pages)
                logger.info(f"PDF has {page_count} pages")

                text = ""
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    page_text = page.extract_text()
                    text += page_text
                    logger.debug(f"Extracted {len(page_text)} chars from page {page_num}/{page_count}")

                # Clean up text
                text = ' '.join(text.split())
                logger.info(f"pypdf extraction successful: {len(text)} characters extracted")
                return text
            except Exception as e:
                logger.error(f"pypdf extraction failed: {str(e)}")
                raise Exception(f"pypdf extraction failed: {str(e)}")

        logger.error("No PDF extraction library available")
        raise Exception("No PDF extraction library available. Please install pypdf or PyMuPDF.")

    def extract_text_from_url(self, url: str) -> str:
        """
        Extract text content from a URL with retry logic

        Args:
            url: The URL to extract text from

        Returns:
            Extracted text content as a string

        Raises:
            Exception: If URL cannot be accessed or parsed after all retries
        """
        logger.info(f"Fetching content from URL: {url}")

        # Detect if URL likely points to a PDF
        is_likely_pdf = url.lower().endswith('.pdf') or '/pdf/' in url.lower()
        if is_likely_pdf:
            logger.info("Detected PDF URL based on extension/path")

        last_error = None
        for attempt in range(self.max_retries):
            try:
                # Add delay before retry attempts (but not on first attempt)
                if attempt > 0:
                    wait_time = self.delay * (2 ** attempt)  # Exponential backoff
                    print(f"  Retry attempt {attempt + 1}/{self.max_retries} after {wait_time}s...")
                    time.sleep(wait_time)

                # Use session for persistent connection
                response = self.session.get(url, timeout=30, allow_redirects=True)
                response.raise_for_status()

                # First, check if content is actually a PDF by looking at magic bytes
                # This must be checked BEFORE UTF-8 decoding check
                content_start = response.content[:4]
                is_pdf_content = content_start == b'%PDF'

                # Also check content type header
                content_type = response.headers.get('content-type', '').lower()
                if 'application/pdf' in content_type:
                    is_pdf_content = True

                # If we have PDF content, extract text from it
                if is_pdf_content:
                    print(f"  Detected PDF content, extracting text...")
                    text = self.extract_text_from_pdf(response.content)
                    if len(text) < 100:
                        print(f"  ⚠ Warning: Extracted PDF content is very short ({len(text)} characters)")
                    print(f"  ✓ Successfully extracted {len(text)} characters from PDF")
                    return text

                # Check for other binary content (non-PDF)
                try:
                    # Try to decode as text - if this fails, it's likely binary
                    response.content.decode('utf-8', errors='strict')
                except UnicodeDecodeError:
                    # If it's not a PDF but still binary, we can't handle it
                    raise Exception("Received binary content that cannot be decoded as text. This may be a PDF - check if the URL serves PDFs.")

                # Parse HTML content
                soup = BeautifulSoup(response.content, 'html.parser')

                # Remove script, style, and other non-content elements
                for element in soup(["script", "style", "nav", "header", "footer", "aside", "iframe"]):
                    element.decompose()

                # Get text
                text = soup.get_text()

                # Clean up text - remove extra whitespace
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = ' '.join(chunk for chunk in chunks if chunk)

                # Check if we got meaningful content (more than just "Redirecting" or similar)
                if len(text) < 100:
                    print(f"  ⚠ Warning: Extracted content is very short ({len(text)} characters)")
                    print(f"  Content: {text}")
                    if attempt < self.max_retries - 1:
                        last_error = Exception(f"Content too short, likely a redirect page")
                        continue

                print(f"  ✓ Successfully extracted {len(text)} characters")
                return text

            except requests.exceptions.RequestException as e:
                last_error = Exception(f"Error fetching URL {url}: {str(e)}")
                print(f"  ✗ {last_error}")
                if attempt == self.max_retries - 1:
                    break
            except Exception as e:
                last_error = e
                print(f"  ✗ {str(e)}")
                break

        # If we get here, all retries failed
        raise last_error if last_error else Exception(f"Failed to extract content from {url}")

    def extract_text_from_local_pdf(self, file_path: str) -> str:
        """
        Extract text from a local PDF file

        Args:
            file_path: Path to the local PDF file

        Returns:
            Extracted text content

        Raises:
            Exception: If file doesn't exist or extraction fails
        """
        if not os.path.exists(file_path):
            raise Exception(f"File not found: {file_path}")

        print(f"  Reading local PDF file: {file_path}")

        with open(file_path, 'rb') as f:
            pdf_content = f.read()

        text = self.extract_text_from_pdf(pdf_content)
        print(f"  ✓ Successfully extracted {len(text)} characters from local PDF")
        return text

    def process_entry(self, entry: Dict) -> Dict:
        """
        Process a single JSON entry - extract text from URL or local file path

        Args:
            entry: Dictionary with 'id', 'document' (URL or file path), and 'metadata' fields

        Returns:
            New dictionary with document field replaced by extracted text
        """
        # Create a copy of the entry
        new_entry = entry.copy()

        # Get the document field (could be URL or file path)
        document = entry['document']

        # Check if it's a URL
        is_url = document.startswith('http://') or document.startswith('https://')

        if not is_url:
            # Treat as local file path
            file_path = document

            # If file doesn't exist, try adding .pdf extension
            if not os.path.exists(file_path) and not file_path.lower().endswith('.pdf'):
                file_path_with_ext = file_path + '.pdf'
                if os.path.exists(file_path_with_ext):
                    file_path = file_path_with_ext

            # Check if file exists now
            if os.path.exists(file_path):
                # Handle local PDF file
                text_content = self.extract_text_from_local_pdf(file_path)
            else:
                raise Exception(f"Local file not found: {document} (also tried {document}.pdf)")
        else:
            # Handle URL
            text_content = self.extract_text_from_url(document)

        # Replace document field with extracted text
        new_entry['document'] = text_content

        return new_entry

    def process_json_file(self, input_file: str, output_dir: str = "data"):
        """
        Process a JSON file containing list of entries
        Each entry will be saved as a separate file in the output directory

        Args:
            input_file: Path to input JSON file (list of entries with URLs)
            output_dir: Directory to save individual JSON files (default: "data")
        """
        print("=" * 80)
        print("DATA EXTRACTOR - Processing JSON File")
        print("=" * 80)

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        print(f"Output directory: {output_dir}")

        # Read input file
        print(f"\n[STEP 1] Reading input file: {input_file}")
        with open(input_file, 'r', encoding='utf-8') as f:
            entries = json.load(f)

        if not isinstance(entries, list):
            entries = [entries]  # Handle single entry

        print(f"Found {len(entries)} entries to process\n")

        # Process each entry
        print("[STEP 2] Extracting text from URLs and saving individual files...")
        processed_count = 0

        for i, entry in enumerate(entries, 1):
            entry_id = entry.get('id', f'unknown_{i}')
            print(f"\n[{i}/{len(entries)}] Processing entry ID: {entry_id}")

            try:
                processed_entry = self.process_entry(entry)

                # Write individual file
                output_file = os.path.join(output_dir, f"{entry_id}.json")
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(processed_entry, f, indent=2, ensure_ascii=False)

                print(f"  ✓ Entry {entry_id} processed successfully")
                print(f"  ✓ Saved to: {output_file}")
                processed_count += 1

                # Add delay between requests
                if i < len(entries):
                    time.sleep(self.delay)

            except Exception as e:
                print(f"  ✗ Failed to process entry {entry_id}: {str(e)}")
                print(f"  Skipping this entry...")

        print(f"\n{'='*80}")
        print(f"PROCESSING COMPLETE")
        print(f"Successfully processed: {processed_count}/{len(entries)} entries")
        print(f"Output directory: {output_dir}/")
        print(f"{'='*80}")

    def process_single_entry_file(self, input_file: str, output_file: str):
        """
        Process a single JSON entry (not a list)

        Args:
            input_file: Path to input JSON file (single entry with URL)
            output_file: Path to output JSON file (single entry with extracted text)
        """
        print("=" * 80)
        print("DATA EXTRACTOR - Processing Single Entry")
        print("=" * 80)

        # Read input file
        print(f"\n[STEP 1] Reading input file: {input_file}")
        with open(input_file, 'r', encoding='utf-8') as f:
            entry = json.load(f)

        print(f"Processing entry ID: {entry.get('id', 'unknown')}\n")

        # Process entry
        print("[STEP 2] Extracting text from URL...")
        try:
            processed_entry = self.process_entry(entry)

            # Write output file
            print(f"\n[STEP 3] Writing output file: {output_file}")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(processed_entry, f, indent=2, ensure_ascii=False)

            print(f"\n{'='*80}")
            print(f"PROCESSING COMPLETE")
            print(f"Output saved to: {output_file}")
            print(f"{'='*80}")

        except Exception as e:
            print(f"\n✗ Failed to process entry: {str(e)}")


if __name__ == "__main__":
    """
    Example usage demonstrating how to use the data extractor
    """
    import sys

    if len(sys.argv) < 2:
        print("Usage: python data_extractor.py <input_file> [output_dir]")
        print("\nExample:")
        print("  python data_extractor.py input_urls.json")
        print("  python data_extractor.py input_urls.json custom_data_dir")
        print("\nOutput:")
        print("  Each entry will be saved as data/[id].json")
        print("  (or custom_data_dir/[id].json if specified)")
        print("\nInput JSON format (list of entries):")
        print("""[
  {
    "id": "sub_001",
    "document": "https://example.com/article",
    "metadata": {
      "faculty_name": "Dr. John Smith",
      "date_published": "2026-01-10T14:30:00Z",
      "content_type": "Award",
      "department": "Computer Science"
    }
  }
]""")
        sys.exit(1)

    input_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "data"

    extractor = DataExtractor(delay=1.0)
    extractor.process_json_file(input_file, output_dir)
