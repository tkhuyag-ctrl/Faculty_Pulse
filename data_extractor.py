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


class DataExtractor:
    """Extracts text content from web URLs in JSON entries"""

    def __init__(self, delay: float = 1.0):
        """
        Initialize the data extractor

        Args:
            delay: Delay in seconds between requests to avoid overwhelming servers
        """
        self.delay = delay
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def extract_text_from_url(self, url: str) -> str:
        """
        Extract text content from a URL

        Args:
            url: The URL to extract text from

        Returns:
            Extracted text content as a string

        Raises:
            Exception: If URL cannot be accessed or parsed
        """
        try:
            print(f"  Fetching content from: {url}")
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()

            # Parse HTML content
            soup = BeautifulSoup(response.content, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Get text
            text = soup.get_text()

            # Clean up text - remove extra whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)

            print(f"  ✓ Successfully extracted {len(text)} characters")
            return text

        except requests.exceptions.RequestException as e:
            error_msg = f"Error fetching URL {url}: {str(e)}"
            print(f"  ✗ {error_msg}")
            raise Exception(error_msg)

    def process_entry(self, entry: Dict) -> Dict:
        """
        Process a single JSON entry - extract text from URL in document field

        Args:
            entry: Dictionary with 'id', 'document' (URL), and 'metadata' fields

        Returns:
            New dictionary with document field replaced by extracted text
        """
        # Create a copy of the entry
        new_entry = entry.copy()

        # Extract the URL from document field
        url = entry['document']

        # Extract text from URL
        text_content = self.extract_text_from_url(url)

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
