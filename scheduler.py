"""
Crawler Scheduler - Automated scheduling for the crawler
Supports daily, weekly, and custom schedules
"""
import schedule
import time
import logging
from datetime import datetime
from automated_crawler import AutomatedCrawler


class CrawlerScheduler:
    """
    Scheduler for automated crawler execution
    """

    def __init__(self, config_file: str = "crawler_config.json"):
        """
        Initialize the scheduler

        Args:
            config_file: Path to crawler configuration file
        """
        self.logger = logging.getLogger(__name__)
        self.crawler = AutomatedCrawler(config_file=config_file)
        self.config = self.crawler.config

        # Setup schedule based on config
        self._setup_schedule()

    def _setup_schedule(self):
        """Setup the schedule based on configuration"""
        schedule_config = self.config.get('schedule', {})

        if not schedule_config.get('enabled', False):
            self.logger.info("Scheduling is disabled in configuration")
            return

        frequency = schedule_config.get('frequency', 'daily')
        run_time = schedule_config.get('time', '02:00')

        if frequency == 'daily':
            schedule.every().day.at(run_time).do(self.run_crawl)
            self.logger.info(f"Scheduled daily crawl at {run_time}")

        elif frequency == 'weekly':
            # Weekly on Monday at specified time
            schedule.every().monday.at(run_time).do(self.run_crawl)
            self.logger.info(f"Scheduled weekly crawl (Mondays) at {run_time}")

        elif frequency == 'hourly':
            schedule.every().hour.do(self.run_crawl)
            self.logger.info("Scheduled hourly crawl")

        else:
            self.logger.warning(f"Unknown schedule frequency: {frequency}")

    def run_crawl(self):
        """Execute a crawl run"""
        self.logger.info("="*80)
        self.logger.info(f"Starting scheduled crawl at {datetime.now()}")
        self.logger.info("="*80)

        try:
            results = self.crawler.crawl_all_pending()

            self.logger.info("Crawl completed successfully")
            self.logger.info(f"Results: {results['successful']}/{results['total']} successful")
            self.logger.info(f"  Updated: {results['updated']}, Unchanged: {results['unchanged']}")

            if results['failed'] > 0:
                self.logger.warning(f"  Failed: {results['failed']}")
                for error in results['errors'][:5]:  # Log first 5 errors
                    self.logger.error(f"    {error['url']}: {error['error']}")

        except Exception as e:
            self.logger.error(f"Crawl failed with error: {str(e)}", exc_info=True)

        self.logger.info("="*80 + "\n")

    def run_once(self):
        """Run the crawler once immediately"""
        self.logger.info("Running one-time crawl...")
        self.run_crawl()
        self.crawler.display_statistics()

    def start(self):
        """Start the scheduler (blocking)"""
        self.logger.info("Crawler scheduler started")
        self.logger.info("Press Ctrl+C to stop")

        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute

        except KeyboardInterrupt:
            self.logger.info("Scheduler stopped by user")
        finally:
            self.crawler.close()


# CLI interface
if __name__ == "__main__":
    import sys

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('scheduler.log')
        ]
    )

    print("="*80)
    print("FACULTY PULSE - CRAWLER SCHEDULER")
    print("="*80)

    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python scheduler.py start    # Start scheduled crawler (blocks)")
        print("  python scheduler.py once     # Run crawler once and exit")
        print("\nConfiguration:")
        print("  Edit crawler_config.json to configure schedule settings")
        sys.exit(0)

    command = sys.argv[1].lower()
    scheduler = CrawlerScheduler()

    if command == "start":
        scheduler.start()

    elif command == "once":
        scheduler.run_once()

    else:
        print(f"Unknown command: {command}")
        print("Available commands: start, once")
        sys.exit(1)
