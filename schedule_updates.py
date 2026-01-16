"""
Schedule Automated Updates
Sets up automatic bi-weekly updates using Windows Task Scheduler or schedule library
"""
import os
import sys
import subprocess
from pathlib import Path


def setup_windows_task_scheduler():
    """
    Create a Windows Task Scheduler task to run updates every 2 weeks
    """
    print("="*80)
    print("SETUP AUTOMATED UPDATES - WINDOWS TASK SCHEDULER")
    print("="*80)

    # Get paths
    script_dir = Path(__file__).parent.absolute()
    python_exe = sys.executable
    script_path = script_dir / "automated_data_updater.py"

    # Task details
    task_name = "FacultyPulse_BiweeklyUpdate"
    task_description = "Automated faculty and publication data update for Faculty Pulse chatbot"

    print(f"\nTask Configuration:")
    print(f"  Name: {task_name}")
    print(f"  Script: {script_path}")
    print(f"  Python: {python_exe}")
    print(f"  Schedule: Every 2 weeks on Sunday at 2:00 AM")
    print("")

    # Build schtasks command
    # Run every 14 days, starting next Sunday at 2 AM
    cmd = [
        "schtasks",
        "/Create",
        "/TN", task_name,
        "/TR", f'"{python_exe}" "{script_path}"',
        "/SC", "WEEKLY",
        "/D", "SUN",
        "/ST", "02:00",
        "/RI", "1008",  # Repeat interval: 1008 minutes = 14 days * 24 hours * 60 minutes / 2 weeks
        "/F"  # Force create (overwrite if exists)
    ]

    print("Creating scheduled task...")
    print(f"Command: {' '.join(cmd)}")
    print("")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)

        if result.returncode == 0:
            print("✓ Scheduled task created successfully!")
            print("")
            print("The automated update will run:")
            print("  - Every 2 weeks on Sunday at 2:00 AM")
            print("  - Next run: Check Task Scheduler for exact date")
            print("")
            print("To manage the task:")
            print("  - Open Task Scheduler (taskschd.msc)")
            print(f"  - Look for: {task_name}")
            print("")
            print("To manually trigger:")
            print(f"  schtasks /Run /TN {task_name}")
            print("")
            print("To disable:")
            print(f"  schtasks /Change /TN {task_name} /DISABLE")
            print("")
            print("To delete:")
            print(f"  schtasks /Delete /TN {task_name} /F")
            return True
        else:
            print(f"✗ Failed to create scheduled task")
            print(f"Error: {result.stderr}")
            print("")
            print("You may need to:")
            print("  1. Run this script as Administrator")
            print("  2. Or manually create the task using Task Scheduler GUI")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        print("")
        print("Alternative: Use Task Scheduler GUI manually")
        return False


def setup_python_scheduler():
    """
    Alternative: Use Python schedule library (requires script to be always running)
    This is less ideal than Windows Task Scheduler but more cross-platform
    """
    print("="*80)
    print("SETUP AUTOMATED UPDATES - PYTHON SCHEDULER")
    print("="*80)
    print("")
    print("This method requires installing 'schedule' library and keeping a script running.")
    print("For Windows, Task Scheduler (option 1) is recommended instead.")
    print("")

    try:
        import schedule
        import time
        from automated_data_updater import AutomatedDataUpdater

        def job():
            """Job to run every 2 weeks"""
            print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Running scheduled update...")
            updater = AutomatedDataUpdater()
            results = updater.run_full_update(days_back=60)
            print(f"Update completed: {results['status']}")

        # Schedule job every 2 weeks
        schedule.every(2).weeks.do(job)

        print("✓ Scheduler configured!")
        print("  Schedule: Every 2 weeks")
        print("")
        print("NOTE: This script must keep running for scheduling to work.")
        print("Press Ctrl+C to stop.")
        print("")

        # Keep script running
        while True:
            schedule.run_pending()
            time.sleep(3600)  # Check every hour

    except ImportError:
        print("✗ 'schedule' library not installed")
        print("")
        print("To use this method:")
        print("  1. Install: pip install schedule")
        print("  2. Run this script again")
        return False


def show_manual_setup_instructions():
    """Show instructions for manual Task Scheduler setup"""
    print("="*80)
    print("MANUAL SETUP INSTRUCTIONS - WINDOWS TASK SCHEDULER")
    print("="*80)

    script_dir = Path(__file__).parent.absolute()
    python_exe = sys.executable
    script_path = script_dir / "automated_data_updater.py"

    print("""
To manually set up automated updates:

1. Open Task Scheduler
   - Press Win+R, type: taskschd.msc
   - Click OK

2. Create Basic Task
   - Click "Create Basic Task" in right panel
   - Name: FacultyPulse_BiweeklyUpdate
   - Description: Automated data update for Faculty Pulse

3. Trigger
   - Select "Weekly"
   - Recur every: 2 weeks
   - Day: Sunday (or your preferred day)
   - Time: 2:00 AM (or your preferred time)

4. Action
   - Select "Start a program"
""")

    print(f"   - Program/script: {python_exe}")
    print(f"   - Add arguments: \"{script_path}\"")
    print(f"   - Start in: {script_dir}")

    print("""
5. Finish
   - Review settings
   - Check "Open Properties dialog"
   - Click Finish

6. Additional Settings (in Properties)
   - General tab:
     * Run whether user is logged on or not (optional)
     * Run with highest privileges (recommended)
   - Conditions tab:
     * Uncheck "Start only if on AC power" if on laptop
   - Settings tab:
     * Check "Run task as soon as possible after scheduled start is missed"

7. Save and test
   - Click OK
   - Right-click task → Run to test immediately
""")


def main():
    """Main setup menu"""
    print("="*80)
    print("FACULTY PULSE - AUTOMATED UPDATE SCHEDULER SETUP")
    print("="*80)
    print("")
    print("Choose setup method:")
    print("  1. Windows Task Scheduler (Recommended)")
    print("  2. Python schedule library (Requires always-running script)")
    print("  3. Show manual setup instructions")
    print("  4. Exit")
    print("")

    choice = input("Enter choice (1-4): ").strip()

    if choice == "1":
        setup_windows_task_scheduler()
    elif choice == "2":
        setup_python_scheduler()
    elif choice == "3":
        show_manual_setup_instructions()
    elif choice == "4":
        print("Exiting...")
    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()
