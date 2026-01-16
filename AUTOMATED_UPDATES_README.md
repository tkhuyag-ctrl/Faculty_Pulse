# Automated Data Collection & Updates

Comprehensive automation system for Faculty Pulse that keeps your database up-to-date automatically.

## Overview

This automation system performs **3 key functions**:

1. **Faculty List Sync** - Checks Haverford website for new/removed faculty
2. **Publication Updates** - Fetches recent publications from OpenAlex
3. **Automatic Scheduling** - Runs updates every 2 weeks automatically

---

## Files Overview

| File | Purpose |
|------|---------|
| `sync_faculty_data.py` | Syncs faculty list from Haverford website |
| `auto_update_publications.py` | Fetches new publications from OpenAlex |
| `automated_data_updater.py` | Main orchestrator (runs both steps) |
| `schedule_updates.py` | Sets up automatic bi-weekly scheduling |

---

## How It Works

### Step 1: Faculty Sync

**Script:** `sync_faculty_data.py`

**What it does:**
1. Loads current faculty from `haverford_faculty_with_openalex.json`
2. Fetches latest faculty list from Haverford website
3. Compares and identifies:
   - **New faculty** (on website but not in local file)
   - **Removed faculty** (in local file but not on website)
   - **Updated faculty** (department changes, etc.)
4. Creates backup of old file
5. Saves updated faculty list

**Output:**
- Updated `haverford_faculty_with_openalex.json`
- Backup file: `haverford_faculty_with_openalex_backup_YYYYMMDD_HHMMSS.json`
- Log file: `faculty_sync_YYYYMMDD_HHMMSS.log`

**Run manually:**
```bash
python sync_faculty_data.py
```

---

### Step 2: Publication Updates

**Script:** `auto_update_publications.py`

**What it does:**
1. Loads all faculty with OpenAlex IDs from JSON file
2. Loads existing publication IDs from ChromaDB
3. For each faculty:
   - Fetches recent publications from OpenAlex (last 60 days by default)
   - Filters out publications already in database
   - Adds only NEW publications to ChromaDB
4. Generates summary report

**Key Features:**
- **Duplicate detection** - Never adds the same publication twice
- **Incremental updates** - Only fetches recent publications (configurable timeframe)
- **Batch processing** - Efficiently processes all faculty
- **Error handling** - Continues even if one faculty fails

**Output:**
- New publications added to ChromaDB
- Log file: `auto_update_pubs_YYYYMMDD_HHMMSS.log`

**Run manually:**
```bash
python auto_update_publications.py
```

---

### Step 3: Full Automated Update

**Script:** `automated_data_updater.py`

**What it does:**
Runs both Step 1 and Step 2 in sequence:
1. Syncs faculty data
2. Updates publications
3. Generates combined report

**Output:**
- All outputs from Step 1 and Step 2
- Results JSON: `automated_update_results_YYYYMMDD_HHMMSS.json`
- Combined log: `automated_update_YYYYMMDD_HHMMSS.log`

**Run manually:**
```bash
python automated_data_updater.py
```

---

## Setting Up Automatic Scheduling

### Method 1: Windows Task Scheduler (Recommended)

**One-time setup:**
```bash
python schedule_updates.py
```

Choose option 1, and the script will:
- Create a scheduled task named `FacultyPulse_BiweeklyUpdate`
- Schedule it to run every 2 weeks on Sunday at 2:00 AM
- Configure it to run automatically even if you're not logged in

**Manage the scheduled task:**

**Check status:**
```bash
schtasks /Query /TN FacultyPulse_BiweeklyUpdate
```

**Run manually (trigger now):**
```bash
schtasks /Run /TN FacultyPulse_BiweeklyUpdate
```

**Disable (stop automatic runs):**
```bash
schtasks /Change /TN FacultyPulse_BiweeklyUpdate /DISABLE
```

**Enable (resume automatic runs):**
```bash
schtasks /Change /TN FacultyPulse_BiweeklyUpdate /ENABLE
```

**Delete (remove completely):**
```bash
schtasks /Delete /TN FacultyPulse_BiweeklyUpdate /F
```

**View in GUI:**
- Press `Win+R`, type `taskschd.msc`, press Enter
- Find task: `FacultyPulse_BiweeklyUpdate`

---

### Method 2: Manual Task Scheduler Setup

If the automatic setup doesn't work (needs admin rights), you can set it up manually:

1. **Open Task Scheduler**
   - Press `Win+R`
   - Type: `taskschd.msc`
   - Click OK

2. **Create Basic Task**
   - Click "Create Basic Task" in right panel
   - Name: `FacultyPulse_BiweeklyUpdate`
   - Description: `Automated data update for Faculty Pulse`
   - Click Next

3. **Set Trigger**
   - Select "Weekly"
   - Click Next
   - Recur every: `2 weeks`
   - Day: Sunday (or your preference)
   - Time: 2:00 AM (or your preference)
   - Click Next

4. **Set Action**
   - Select "Start a program"
   - Click Next
   - Program/script: Path to your Python executable
     - Example: `C:\Users\menah\AppData\Local\Programs\Python\Python311\python.exe`
     - Find yours: `where python` in command prompt
   - Add arguments: `"C:\Users\menah\Faculty_Pulse\automated_data_updater.py"`
   - Start in: `C:\Users\menah\Faculty_Pulse`
   - Click Next

5. **Finish**
   - Review settings
   - Check "Open the Properties dialog for this task when I click Finish"
   - Click Finish

6. **Configure Properties** (optional but recommended)
   - **General tab:**
     - Check "Run whether user is logged on or not"
     - Check "Run with highest privileges"
   - **Conditions tab:**
     - Uncheck "Start the task only if the computer is on AC power"
   - **Settings tab:**
     - Check "Run task as soon as possible after a scheduled start is missed"
   - Click OK

7. **Test**
   - Right-click the task → Run
   - Check logs to verify it worked

---

## Configuration Options

### Customizing Update Frequency

**Edit the scheduled task:**
- 2 weeks (default): `Recur every 2 weeks`
- Weekly: `Recur every 1 week`
- Monthly: `Recur every 4 weeks`

**Or modify in code:**

In `automated_data_updater.py`, change:
```python
# Default: 60 days lookback (good for bi-weekly runs)
results = updater.run_full_update(days_back=60)

# For weekly runs, use 30 days:
results = updater.run_full_update(days_back=30)

# For monthly runs, use 90 days:
results = updater.run_full_update(days_back=90)
```

---

### Customizing Faculty Website Parsing

The faculty sync uses web scraping to detect changes on Haverford's website.

**IMPORTANT:** You need to update the HTML selectors in `sync_faculty_data.py` to match the actual website structure.

**To customize:**

1. Open `sync_faculty_data.py`
2. Find the `fetch_current_faculty_from_website()` method
3. Update the BeautifulSoup selectors:

```python
# Example - adjust based on actual website HTML:
faculty_cards = soup.find_all('div', class_='faculty-card')

for card in faculty_cards:
    name_elem = card.find('h3', class_='faculty-name')
    dept_elem = card.find('span', class_='department')
    profile_elem = card.find('a', class_='profile-link')
```

**How to find the right selectors:**
1. Visit https://www.haverford.edu/users/faculty
2. Right-click on a faculty member's name → "Inspect"
3. Look at the HTML structure
4. Update the selectors accordingly

---

## Monitoring & Logs

### Where to Find Logs

All operations create timestamped log files:

**Faculty sync:**
```
faculty_sync_YYYYMMDD_HHMMSS.log
```

**Publication updates:**
```
auto_update_pubs_YYYYMMDD_HHMMSS.log
```

**Combined automated updates:**
```
automated_update_YYYYMMDD_HHMMSS.log
```

**Results JSON (for automation):**
```
automated_update_results_YYYYMMDD_HHMMSS.json
```

### What to Monitor

**Faculty sync logs show:**
- New faculty added
- Faculty removed
- Department changes
- Total faculty count

**Publication update logs show:**
- Faculty processed
- New publications added per faculty
- Duplicates skipped
- Errors encountered
- Total publications in database

### Setting Up Notifications

**Option 1: Email notifications on task failure**

In Task Scheduler Properties:
1. Go to "Actions" tab
2. Add new action: "Send an e-mail" (if available)
3. Configure email settings

**Option 2: Check logs programmatically**

Create a monitoring script that checks logs and sends alerts if errors occur.

---

## Troubleshooting

### Task doesn't run automatically

**Check:**
1. Task Scheduler is running: `sc query Schedule`
2. Task is enabled: Check in Task Scheduler GUI
3. Computer was on at scheduled time
4. Check "Last Run Result" in Task Scheduler (0x0 = success)

**Fix:**
- Make sure "Run task as soon as possible after a scheduled start is missed" is checked
- Check event logs: Event Viewer → Windows Logs → Application

### Faculty sync finds no faculty

**Possible causes:**
1. Website structure changed (update BeautifulSoup selectors)
2. Network connection issue
3. Website is down or blocking requests

**Debug:**
- Run `python sync_faculty_data.py` manually
- Check log file for errors
- Visit website in browser to verify structure

### Publication updates fail

**Possible causes:**
1. OpenAlex API down or rate limited
2. Network connectivity issues
3. ChromaDB corruption

**Fix:**
- Check OpenAlex API status: https://docs.openalex.org/
- Verify network connection
- Check ChromaDB: `python -c "from chroma_manager import ChromaDBManager; c = ChromaDBManager(); print(c.collection.count())"`

### Duplicates being added

This shouldn't happen (duplicate detection is built-in), but if it does:

**Check:**
- Are work IDs being stored correctly?
- Run: `python -c "from auto_update_publications import AutoPublicationUpdater; u = AutoPublicationUpdater(); u.load_existing_publications(); print(len(u.existing_work_ids))"`

---

## Testing Before Scheduling

**Before setting up automatic scheduling, test manually:**

```bash
# Test faculty sync
python sync_faculty_data.py

# Test publication updates
python auto_update_publications.py

# Test combined run
python automated_data_updater.py
```

**Verify outputs:**
1. Check log files for errors
2. Verify `haverford_faculty_with_openalex.json` was updated
3. Check ChromaDB count: should increase if new publications were found
4. Review results JSON for statistics

---

## Performance & Resource Usage

### Expected Runtime

- **Faculty sync:** 10-30 seconds (depends on website response time)
- **Publication updates:** 5-15 minutes for ~50 faculty
  - ~5-10 seconds per faculty
  - Longer if many new publications found

**Total runtime:** ~15-20 minutes for complete update

### Resource Usage

- **Network:** Moderate (API calls to OpenAlex)
- **CPU:** Low (mostly I/O bound)
- **Memory:** ~100-200 MB
- **Disk:** Logs + database growth
  - Logs: ~1-5 MB per run
  - Database: ~50 KB per publication

### Rate Limits

**OpenAlex API:**
- No official limit for polite usage
- Built-in delays: 0.1s between pagination requests
- User-Agent identifies as Faculty Pulse project

**Haverford website:**
- No known rate limits
- Single request per sync

---

## Best Practices

1. **Test first** - Always test manually before scheduling
2. **Monitor logs** - Check logs after first few scheduled runs
3. **Keep backups** - Faculty sync auto-creates backups, but consider additional backups
4. **Update selectors** - If Haverford website changes, update BeautifulSoup selectors
5. **Check for errors** - Review logs periodically for any issues
6. **Adjust frequency** - Bi-weekly is good balance, but adjust based on your needs

---

## Quick Reference

### Run manually

```bash
# Full update (both steps)
python automated_data_updater.py

# Just faculty sync
python sync_faculty_data.py

# Just publication updates
python auto_update_publications.py
```

### Setup automatic scheduling

```bash
python schedule_updates.py
```

### Manage scheduled task

```bash
# Check status
schtasks /Query /TN FacultyPulse_BiweeklyUpdate

# Run now
schtasks /Run /TN FacultyPulse_BiweeklyUpdate

# Disable
schtasks /Change /TN FacultyPulse_BiweeklyUpdate /DISABLE

# Delete
schtasks /Delete /TN FacultyPulse_BiweeklyUpdate /F
```

---

## Summary

You now have a complete automated data collection system:

✅ **Faculty sync** - Automatically detects faculty changes
✅ **Publication updates** - Fetches new research from OpenAlex
✅ **Duplicate prevention** - Never adds same publication twice
✅ **Automatic scheduling** - Runs every 2 weeks unattended
✅ **Comprehensive logging** - Track all changes and errors
✅ **Backup system** - Auto-creates backups before changes

The system will keep your Faculty Pulse database up-to-date with minimal manual intervention!
