# Automation Quick Start Guide

Get automated updates running in 5 minutes!

## What This Does

Automatically updates your Faculty Pulse database every 2 weeks:
- ✅ Syncs faculty list from Haverford website
- ✅ Fetches new publications from OpenAlex
- ✅ Runs unattended - no manual work needed

---

## Setup (One-Time)

### Step 1: Test Manual Run

First, verify everything works:

```bash
cd C:\Users\menah\Faculty_Pulse
python automated_data_updater.py
```

**Watch for:**
- Faculty sync completes
- Publications update runs
- "✓ AUTOMATED UPDATE COMPLETED SUCCESSFULLY" message

**If errors occur:** Check the log files and fix issues before scheduling.

---

### Step 2: Set Up Automatic Scheduling

```bash
python schedule_updates.py
```

- Choose option **1** (Windows Task Scheduler)
- Wait for confirmation: "✓ Scheduled task created successfully!"

**That's it!** Updates will now run automatically every 2 weeks on Sunday at 2 AM.

---

### Step 3: Test Scheduled Task (Optional)

Manually trigger the task to verify it works:

```bash
schtasks /Run /TN FacultyPulse_BiweeklyUpdate
```

Check the log file to confirm success.

---

## Verifying It's Working

### After First Scheduled Run

**Check logs folder for new files:**
```
automated_update_YYYYMMDD_HHMMSS.log
```

**Look for:**
- "AUTOMATED UPDATE COMPLETED SUCCESSFULLY"
- Faculty changes (if any)
- New publications added (if any)

**Verify in Streamlit app:**
- Restart the app: The new publications should be searchable
- Try query: "recent publications"

---

## Managing the Schedule

### View Next Run Time

```bash
schtasks /Query /TN FacultyPulse_BiweeklyUpdate /FO LIST
```

Look for "Next Run Time"

### Run Manually Now

```bash
schtasks /Run /TN FacultyPulse_BiweeklyUpdate
```

### Disable (Stop Automatic Runs)

```bash
schtasks /Change /TN FacultyPulse_BiweeklyUpdate /DISABLE
```

### Enable (Resume Automatic Runs)

```bash
schtasks /Change /TN FacultyPulse_BiweeklyUpdate /ENABLE
```

### Remove Completely

```bash
schtasks /Delete /TN FacultyPulse_BiweeklyUpdate /F
```

---

## Troubleshooting

### "Access Denied" when creating scheduled task

**Solution:** Run as Administrator:
1. Right-click Command Prompt
2. Select "Run as administrator"
3. Navigate to your folder: `cd C:\Users\menah\Faculty_Pulse`
4. Run again: `python schedule_updates.py`

### Task doesn't run automatically

**Check if task exists:**
```bash
schtasks /Query /TN FacultyPulse_BiweeklyUpdate
```

**If not found:** Re-run setup:
```bash
python schedule_updates.py
```

**If exists but not running:**
- Open Task Scheduler GUI (`taskschd.msc`)
- Find task: `FacultyPulse_BiweeklyUpdate`
- Check "Last Run Result" (should be `0x0` for success)
- Right-click → Properties → Settings tab
- Enable "Run task as soon as possible after a scheduled start is missed"

### Faculty sync finds no new faculty

**This is normal!** If the faculty list hasn't changed, the sync will show:
- New: 0
- Removed: 0
- Updated: 0

### No new publications

**Also normal!** If faculty haven't published in the last 60 days, you'll see:
- New publications: 0

This means everything is working - there's just no new data.

---

## What Happens Each Run

1. **Faculty Sync** (~10-30 seconds)
   - Checks Haverford website for faculty changes
   - Updates local JSON file if needed
   - Creates backup before any changes

2. **Publication Update** (~5-15 minutes)
   - Checks OpenAlex for new publications (last 60 days)
   - Only adds publications not already in database
   - Updates ChromaDB with new entries

3. **Logging & Reports**
   - Creates timestamped log files
   - Saves results JSON with statistics
   - All files kept for your records

---

## Customization

### Change Update Frequency

**Default:** Every 2 weeks

**To change to weekly:**
1. Open Task Scheduler (`taskschd.msc`)
2. Find task: `FacultyPulse_BiweeklyUpdate`
3. Right-click → Properties → Triggers tab
4. Edit trigger → Change "Recur every 2 weeks" to "1 week"
5. Click OK

**To change to monthly:**
- Same steps, but use "4 weeks"

### Change Day/Time

1. Open Task Scheduler (`taskschd.msc`)
2. Find task → Properties → Triggers tab
3. Edit trigger
4. Change day and/or start time
5. Click OK

### Update Website Selectors

**If Haverford's website structure changes:**

1. Open `sync_faculty_data.py`
2. Find method: `fetch_current_faculty_from_website()`
3. Update BeautifulSoup selectors to match new HTML structure
4. Test: `python sync_faculty_data.py`

See [AUTOMATED_UPDATES_README.md](AUTOMATED_UPDATES_README.md) for detailed instructions.

---

## Files Created

After setup, you'll have:

**Core scripts:**
- `sync_faculty_data.py` - Faculty list sync
- `auto_update_publications.py` - Publication updates
- `automated_data_updater.py` - Main orchestrator
- `schedule_updates.py` - Scheduler setup

**Generated files (per run):**
- `automated_update_YYYYMMDD_HHMMSS.log` - Combined log
- `automated_update_results_YYYYMMDD_HHMMSS.json` - Stats
- `haverford_faculty_with_openalex_backup_YYYYMMDD_HHMMSS.json` - Faculty backup

**Location:** All in `C:\Users\menah\Faculty_Pulse\`

---

## Need Help?

**Check full documentation:** [AUTOMATED_UPDATES_README.md](AUTOMATED_UPDATES_README.md)

**Common issues:**
- "Access denied" → Run as administrator
- "Faculty sync failed" → Website structure may have changed
- "Publication update failed" → Check network/OpenAlex API status

**Test manually first:**
```bash
python automated_data_updater.py
```

If manual runs work but scheduled runs don't, it's a Task Scheduler configuration issue.

---

## Summary

✅ **You've set up automated bi-weekly updates!**

**What happens now:**
- Every 2 weeks (Sunday 2 AM by default)
- System checks for faculty changes
- Fetches new publications from last 60 days
- Updates database automatically
- Creates logs for your review

**No further action needed!** Just check logs occasionally to see what's being updated.

**To verify:** Check logs after the first scheduled run or trigger manually:
```bash
schtasks /Run /TN FacultyPulse_BiweeklyUpdate
```

Enjoy your automated Faculty Pulse system! 🎉
