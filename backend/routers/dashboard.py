from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from services.sheets import read_sheet, get_all_job_titles, get_source_sheet_name, ensure_sheet_exists
# NEW import
from services.sheets import get_all_sheet_titles, batch_read_sheets

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/stats")
def get_dashboard_stats():
    """
    Returns aggregated statistics for the dashboard.
    Optimized to use BATCH fetching (2 API calls total instead of 2N+1).
    Now robust: Checks if sheets exist before requesting them.
    """
    try:
        job_titles = get_all_job_titles()
        sheet_titles = get_all_sheet_titles()
        existing_sheets_set = set(sheet_titles)
        
        # Prepare ranges for batch fetching
        ranges = []
        # Store mapping to help processing later
        # key: job_title -> { "received_range": "...", "analysis_range": "..." }
        range_map = {} 
        
        for job in job_titles:
            # Range 1: Received Sheet (Job Title)
            # Only add to batch if it exists
            r1 = f"'{job}'!A:A"
            # Logic: If job name is in sheet titles (exact match)
            # Note: A1 notation requires single quotes for names with spaces. 
            # We construct the range string safely.
            r1_key = ""
            if job in existing_sheets_set:
                ranges.append(r1)
                r1_key = r1
            
            # Range 2: Analysis Sheet
            analysis_sheet_name = f"Analysis - {job}"
            r2 = f"'{analysis_sheet_name}'!A:G"
            r2_key = ""
            if analysis_sheet_name in existing_sheets_set:
                ranges.append(r2)
                r2_key = r2
            
            range_map[job] = {
                "received_range": r1_key,
                "analysis_range": r2_key
            }
            
        print(f"DEBUG: Batch fetching {len(ranges)} ranges for dashboard...")
        
        # Execute Batch Read
        batch_results = {}
        if ranges:
            batch_results = batch_read_sheets(ranges)
        
        total_received = 0
        total_processed = 0
        total_passed = 0
        total_selected = 0
        
        job_stats = []
        
        for job in job_titles:
            stats = {
                "job_title": job,
                "received": 0,
                "processed": 0,
                "passed": 0,
                "selected": 0
            }
            
            # --- Process RECEIVED ---
            r_rec_key = range_map[job]["received_range"]
            # If r_rec_key is empty, it meant the sheet didn't exist, so result is naturally empty
            rows_rec = batch_results.get(r_rec_key, []) if r_rec_key else []
            
            if rows_rec:
                # Exclude header if present
                stats["received"] = max(0, len(rows_rec) - 1)
            
            # --- Process PROCESSED & PASSED ---
            r_ana_key = range_map[job]["analysis_range"]
            rows_ana = batch_results.get(r_ana_key, []) if r_ana_key else []
            
            if rows_ana and len(rows_ana) > 1:
                stats["processed"] = len(rows_ana) - 1
                
                pass_count = 0
                for r in rows_ana[1:]:
                    if len(r) > 6:
                        verdict = r[6].strip().upper()
                        if verdict == "PASS":
                            pass_count += 1
                
                stats["passed"] = pass_count
                stats["selected"] = pass_count
                
            job_stats.append(stats)
            
            # Accumulate
            total_received += stats["received"]
            total_processed += stats["processed"]
            total_passed += stats["passed"]
            total_selected += stats["selected"]
            
        return {
            "total_received": total_received,
            "total_processed": total_processed,
            "total_passed": total_passed,
            "total_selected": total_selected,
            "job_stats": job_stats
        }

    except Exception as e:
        print(f"Dashboard Stats Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
