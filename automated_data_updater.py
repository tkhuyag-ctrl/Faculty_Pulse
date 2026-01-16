"""
Automated Data Updater - Main Orchestrator
Runs both faculty sync and publication updates in sequence
Can be scheduled to run automatically every 2 weeks
"""
import json
import logging
from datetime import datetime
from typing import Dict
from sync_faculty_data import FacultySyncer
from auto_update_publications import AutoPublicationUpdater

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'automated_update_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)

logger = logging.getLogger(__name__)


class AutomatedDataUpdater:
    """Orchestrates automated faculty and publication updates"""

    def __init__(self):
        self.faculty_syncer = FacultySyncer()
        self.publication_updater = AutoPublicationUpdater()

    def run_full_update(self, days_back: int = 60) -> Dict:
        """
        Run complete automated update:
        1. Sync faculty data from Haverford website
        2. Update publications from OpenAlex

        Args:
            days_back: How many days back to check for new publications (default: 60 = ~2 months)

        Returns:
            Dict with combined results
        """
        logger.info("="*80)
        logger.info("AUTOMATED DATA UPDATE - FULL RUN")
        logger.info("="*80)
        logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("")

        overall_results = {
            'timestamp': datetime.now().isoformat(),
            'faculty_sync': {},
            'publication_update': {},
            'status': 'unknown'
        }

        # STEP 1: Sync Faculty Data
        logger.info("\n" + "="*80)
        logger.info("STEP 1: SYNCING FACULTY DATA")
        logger.info("="*80)

        try:
            faculty_results = self.faculty_syncer.sync_faculty()
            overall_results['faculty_sync'] = faculty_results

            if faculty_results['status'] == 'success':
                logger.info("✓ Faculty sync completed successfully")
            else:
                logger.error("✗ Faculty sync failed")
                overall_results['status'] = 'failed_faculty_sync'
                return overall_results

        except Exception as e:
            logger.error(f"✗ Faculty sync crashed: {e}")
            overall_results['faculty_sync'] = {'status': 'crashed', 'error': str(e)}
            overall_results['status'] = 'failed_faculty_sync'
            return overall_results

        # STEP 2: Update Publications
        logger.info("\n" + "="*80)
        logger.info("STEP 2: UPDATING PUBLICATIONS")
        logger.info("="*80)

        try:
            publication_results = self.publication_updater.update_all_faculty(days_back=days_back)
            overall_results['publication_update'] = publication_results

            if publication_results['status'] == 'success':
                logger.info("✓ Publication update completed successfully")
            else:
                logger.error("✗ Publication update failed")
                overall_results['status'] = 'failed_publication_update'
                return overall_results

        except Exception as e:
            logger.error(f"✗ Publication update crashed: {e}")
            overall_results['publication_update'] = {'status': 'crashed', 'error': str(e)}
            overall_results['status'] = 'failed_publication_update'
            return overall_results

        # SUCCESS
        overall_results['status'] = 'success'

        # Final Summary
        logger.info("\n" + "="*80)
        logger.info("FINAL SUMMARY")
        logger.info("="*80)
        logger.info("Faculty Sync:")
        logger.info(f"  New: {len(faculty_results.get('new_faculty', []))}")
        logger.info(f"  Removed: {len(faculty_results.get('removed_faculty', []))}")
        logger.info(f"  Updated: {len(faculty_results.get('updated_faculty', []))}")
        logger.info(f"  Total: {faculty_results.get('total_faculty', 0)}")

        logger.info("\nPublication Update:")
        logger.info(f"  New publications: {publication_results.get('total_new', 0)}")
        logger.info(f"  Faculty with updates: {len(publication_results.get('faculty_with_new', []))}")
        logger.info(f"  Total in database: {len(self.publication_updater.existing_work_ids)}")

        logger.info(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Save results to JSON
        results_file = f"automated_update_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(overall_results, f, indent=2)
        logger.info(f"\nResults saved to: {results_file}")

        return overall_results


def main():
    """Run automated update"""
    print("="*80)
    print("FACULTY PULSE - AUTOMATED DATA UPDATER")
    print("="*80)
    print("This will:")
    print("  1. Sync faculty list from Haverford website")
    print("  2. Update publications from OpenAlex")
    print("")

    updater = AutomatedDataUpdater()

    # Run with 60 days lookback (good for bi-weekly runs with buffer)
    results = updater.run_full_update(days_back=60)

    print("\n" + "="*80)
    if results['status'] == 'success':
        print("✓ AUTOMATED UPDATE COMPLETED SUCCESSFULLY")
        print("="*80)
        print("\nFaculty Changes:")
        print(f"  New: {len(results['faculty_sync'].get('new_faculty', []))}")
        print(f"  Removed: {len(results['faculty_sync'].get('removed_faculty', []))}")
        print(f"  Updated: {len(results['faculty_sync'].get('updated_faculty', []))}")

        print("\nPublication Updates:")
        print(f"  New publications: {results['publication_update'].get('total_new', 0)}")
        print(f"  Faculty with updates: {len(results['publication_update'].get('faculty_with_new', []))}")
    else:
        print("✗ AUTOMATED UPDATE FAILED")
        print("="*80)
        print(f"Status: {results['status']}")
        print("Check the log file for details")


if __name__ == "__main__":
    main()
