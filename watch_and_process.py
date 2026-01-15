"""
Publication Watcher and Auto-Processor

Automatically monitors for new publications from multiple sources and processes them:
- OpenAlex API (checks for new publications periodically)
- Haverford Scholarship website (via crawler)
- File system (watches for new JSON files)

Usage:
    # Run once to check and process new publications
    python watch_and_process.py --once

    # Run on schedule (check every 24 hours)
    python watch_and_process.py --schedule 24

    # Watch a specific directory for new JSON files
    python watch_and_process.py --watch-dir ./new_publications
"""

import argparse
import json
import logging
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from auto_process_publications import PublicationProcessor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('watcher.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


class PublicationWatcher:
    """
    Monitors and auto-processes new publications from multiple sources
    """

    def __init__(self, state_file: str = "watcher_state.json"):
        """
        Initialize the watcher

        Args:
            state_file: File to store watcher state (last check times, etc.)
        """
        self.processor = PublicationProcessor()
        self.state_file = Path(state_file)
        self.state = self._load_state()

    def _load_state(self) -> Dict:
        """Load watcher state from file"""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                return json.load(f)
        return {
            'last_openalex_check': None,
            'last_crawler_check': None,
            'processed_files': [],
            'total_processed': 0
        }

    def _save_state(self):
        """Save watcher state to file"""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def check_openalex_for_updates(self, faculty_file: str = "haverford_faculty_filtered_no_history.json") -> Dict:
        """
        Check OpenAlex API for new publications since last check

        Args:
            faculty_file: Faculty data file

        Returns:
            Processing statistics
        """
        logger.info("Checking OpenAlex for new publications...")

        # For now, just process the file - in production, you'd query OpenAlex API
        # with a filter for publications newer than self.state['last_openalex_check']

        stats = self.processor.process_from_json_file(faculty_file, skip_existing=True)

        # Update state
        self.state['last_openalex_check'] = datetime.now().isoformat()
        self._save_state()

        return stats

    def check_crawler_results(self, crawler_dir: str = "./") -> Dict:
        """
        Check for new crawler results (Haverford Scholarship, etc.)

        Args:
            crawler_dir: Directory containing crawler output files

        Returns:
            Processing statistics
        """
        logger.info("Checking for new crawler results...")

        crawler_files = [
            "haverford_all_faculty.json",
            "cs_faculty_urls.json",
            "haverford_discovered.json"
        ]

        all_stats = {
            'total': 0,
            'processed': 0,
            'full_text': 0,
            'paywall': 0,
            'not_found': 0,
            'chunked': 0,
            'failed': 0
        }

        for filename in crawler_files:
            filepath = Path(crawler_dir) / filename

            if not filepath.exists():
                continue

            # Skip if already processed
            if str(filepath) in self.state.get('processed_files', []):
                continue

            logger.info(f"Processing new file: {filename}")

            try:
                stats = self.processor.process_from_json_file(str(filepath), skip_existing=True)

                # Aggregate statistics
                for key in all_stats:
                    all_stats[key] += stats.get(key, 0)

                # Mark as processed
                if 'processed_files' not in self.state:
                    self.state['processed_files'] = []
                self.state['processed_files'].append(str(filepath))

            except Exception as e:
                logger.error(f"Error processing {filename}: {e}")

        # Update state
        self.state['last_crawler_check'] = datetime.now().isoformat()
        self.state['total_processed'] = self.state.get('total_processed', 0) + all_stats['processed']
        self._save_state()

        return all_stats

    def watch_directory(self, watch_dir: str, interval_seconds: int = 60):
        """
        Watch a directory for new JSON files and process them

        Args:
            watch_dir: Directory to watch
            interval_seconds: Check interval in seconds
        """
        watch_path = Path(watch_dir)

        if not watch_path.exists():
            logger.error(f"Watch directory does not exist: {watch_dir}")
            return

        logger.info(f"Watching directory: {watch_dir}")
        logger.info(f"Check interval: {interval_seconds} seconds")
        logger.info("Press Ctrl+C to stop")

        processed_files = set(self.state.get('processed_files', []))

        try:
            while True:
                # Find all JSON files
                json_files = list(watch_path.glob("**/*.json"))

                for filepath in json_files:
                    filepath_str = str(filepath)

                    # Skip if already processed
                    if filepath_str in processed_files:
                        continue

                    logger.info(f"\nNew file detected: {filepath.name}")

                    try:
                        stats = self.processor.process_from_json_file(filepath_str, skip_existing=True)

                        # Mark as processed
                        processed_files.add(filepath_str)
                        self.state['processed_files'] = list(processed_files)
                        self.state['total_processed'] = self.state.get('total_processed', 0) + stats['processed']
                        self._save_state()

                        logger.info(f"Processed {stats['processed']} publications from {filepath.name}")

                    except Exception as e:
                        logger.error(f"Error processing {filepath.name}: {e}")

                # Wait before next check
                time.sleep(interval_seconds)

        except KeyboardInterrupt:
            logger.info("\nWatcher stopped by user")

    def run_once(self, check_openalex: bool = True, check_crawler: bool = True) -> Dict:
        """
        Run a single check for new publications

        Args:
            check_openalex: Check OpenAlex for updates
            check_crawler: Check crawler results

        Returns:
            Combined processing statistics
        """
        logger.info("\n" + "="*80)
        logger.info("CHECKING FOR NEW PUBLICATIONS")
        logger.info("="*80 + "\n")

        all_stats = {
            'total': 0,
            'processed': 0,
            'full_text': 0,
            'paywall': 0,
            'not_found': 0,
            'chunked': 0,
            'failed': 0
        }

        if check_openalex:
            try:
                stats = self.check_openalex_for_updates()
                for key in all_stats:
                    all_stats[key] += stats.get(key, 0)
            except Exception as e:
                logger.error(f"Error checking OpenAlex: {e}")

        if check_crawler:
            try:
                stats = self.check_crawler_results()
                for key in all_stats:
                    all_stats[key] += stats.get(key, 0)
            except Exception as e:
                logger.error(f"Error checking crawler results: {e}")

        logger.info("\n" + "="*80)
        logger.info("CHECK COMPLETE")
        logger.info("="*80)
        logger.info(f"New publications processed: {all_stats['processed']}")
        logger.info(f"  - Full text: {all_stats['full_text']}")
        logger.info(f"  - Paywall: {all_stats['paywall']}")
        logger.info(f"  - Not found: {all_stats['not_found']}")
        logger.info(f"  - Chunked: {all_stats['chunked']}")
        logger.info("="*80 + "\n")

        return all_stats

    def run_scheduled(self, interval_hours: int = 24):
        """
        Run on a schedule, checking for new publications periodically

        Args:
            interval_hours: Hours between checks
        """
        logger.info("\n" + "="*80)
        logger.info("SCHEDULED PUBLICATION MONITORING")
        logger.info("="*80)
        logger.info(f"Check interval: Every {interval_hours} hours")
        logger.info("Press Ctrl+C to stop")
        logger.info("="*80 + "\n")

        try:
            while True:
                # Run check
                self.run_once()

                # Wait until next check
                next_check = datetime.now() + timedelta(hours=interval_hours)
                logger.info(f"Next check: {next_check.strftime('%Y-%m-%d %H:%M:%S')}")
                time.sleep(interval_hours * 3600)

        except KeyboardInterrupt:
            logger.info("\nScheduled monitoring stopped by user")


def main():
    """Main execution"""
    parser = argparse.ArgumentParser(
        description="Automated publication monitoring and processing"
    )

    parser.add_argument(
        '--once',
        action='store_true',
        help='Run once and exit'
    )

    parser.add_argument(
        '--schedule',
        type=int,
        metavar='HOURS',
        help='Run on schedule (check every N hours)'
    )

    parser.add_argument(
        '--watch-dir',
        type=str,
        metavar='PATH',
        help='Watch directory for new JSON files'
    )

    parser.add_argument(
        '--watch-interval',
        type=int,
        default=60,
        metavar='SECONDS',
        help='Directory watch interval in seconds (default: 60)'
    )

    parser.add_argument(
        '--no-openalex',
        action='store_true',
        help='Skip OpenAlex check'
    )

    parser.add_argument(
        '--no-crawler',
        action='store_true',
        help='Skip crawler results check'
    )

    args = parser.parse_args()

    watcher = PublicationWatcher()

    if args.watch_dir:
        # Watch directory mode
        watcher.watch_directory(args.watch_dir, args.watch_interval)

    elif args.schedule:
        # Scheduled mode
        watcher.run_scheduled(args.schedule)

    elif args.once:
        # Run once mode
        watcher.run_once(
            check_openalex=not args.no_openalex,
            check_crawler=not args.no_crawler
        )

    else:
        # Default: run once
        print("\nNo mode specified. Running once.")
        print("Use --help to see available options.\n")
        watcher.run_once()


if __name__ == "__main__":
    main()
