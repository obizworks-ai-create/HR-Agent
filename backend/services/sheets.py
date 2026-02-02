import os
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

SPREADSHEET_ID = os.getenv('GOOGLE_SPREADSHEET_ID')
print(f"DEBUG: Loaded SPREADSHEET_ID: {SPREADSHEET_ID}")

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


def get_credentials():
    creds_path = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
    if not creds_path:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON not set")
    
    if os.path.exists(creds_path):
        return Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    else:
        # Assuming content is passed directly
        info = json.loads(creds_path)
        return Credentials.from_service_account_info(info, scopes=SCOPES)

def get_service():
    creds = get_credentials()
    return build('sheets', 'v4', credentials=creds)

def read_sheet(range_name: str, value_render_option: str = 'FORMATTED_VALUE') -> List[List[Any]]:
    service = get_service()
    sheet = service.spreadsheets()
    result = sheet.values().get(
        spreadsheetId=SPREADSHEET_ID, 
        range=range_name, 
        valueRenderOption=value_render_option
    ).execute()
    return result.get('values', [])

def batch_read_sheets(ranges: List[str], value_render_option: str = 'FORMATTED_VALUE') -> Dict[str, List[List[Any]]]:
    """
    Reads multiple ranges in a single API call.
    Returns a dictionary mapping range_name -> values list.
    """
    if not ranges:
        return {}
        
    service = get_service()
    sheet = service.spreadsheets()
    
    try:
        result = sheet.values().batchGet(
            spreadsheetId=SPREADSHEET_ID,
            ranges=ranges,
            valueRenderOption=value_render_option
        ).execute()
        
        valueRanges = result.get('valueRanges', [])
        
        # Map back to requested ranges
        # Note: API returns them in order, but let's be safe and map by returned range if possible,
        # or fall back to index matching since the API guarantees order.
        
        # Google Sheets API returns the actual range (e.g., "Sheet1!A1:B2") which might differ slightly from requested "Sheet1!A:B"
        # So using index is safer if we trust the order.
        
        results_map = {}
        for i, val_range in enumerate(valueRanges):
            # Key = the requested range string (for easy lookup by caller)
            req_range = ranges[i] 
            values = val_range.get('values', [])
            results_map[req_range] = values
            
        return results_map
        
    except Exception as e:
        print(f"❌ Batch Read Error: {e}")
        return {}

def append_to_sheet(range_name: str, values: List[List[Any]]):
    service = get_service()
    body = {
        'values': values
    }
    result = service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID, range=range_name,
        valueInputOption='USER_ENTERED', body=body).execute()
    return result

def write_to_sheet(range_name: str, values: List[List[Any]]):
    service = get_service()
    body = {
        'values': values
    }
    result = service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID, range=range_name,
        valueInputOption='USER_ENTERED', body=body).execute()
    return result

def clear_sheet(sheet_name: str):
    service = get_service()
    # Clears the entire sheet content
    result = service.spreadsheets().values().clear(
        spreadsheetId=SPREADSHEET_ID, range=sheet_name).execute()
    return result

def ensure_sheet_exists(sheet_name: str, headers: List[str] = None):
    service = get_service()
    spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    sheets = spreadsheet.get('sheets', [])
    sheet_titles = [s['properties']['title'] for s in sheets]
    
    if sheet_name not in sheet_titles:
        # Create sheet
        body = {
            'requests': [{
                'addSheet': {
                    'properties': {
                        'title': sheet_name
                    }
                }
            }]
        }
        service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body).execute()
        
        # Add headers if provided
        if headers:
            append_to_sheet(f"{sheet_name}!A1", [headers])
    else:
        # Sheet exists! Verify and Update Headers if requested
        # This fixes the issue where added columns (Email/Contact) don't get headers on existing sheets.
        if headers:
            # We force update the first row to match the new desired headers.
            # This is safe because headers are fixed.
            # Convert list of strings to list of lists [ [ "H1", "H2" ... ] ]
            write_to_sheet(f"{sheet_name}!A1", [headers])

def get_source_sheet_name():
    service = get_service()
    spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    sheets = spreadsheet.get('sheets', [])
    sheet_titles = [s['properties']['title'] for s in sheets]
    
    # Priority: Env Var -> "Candidates" -> First non-system sheet
    env_name = os.getenv("CANDIDATE_SOURCE_SHEET")
    if env_name and env_name in sheet_titles:
        return env_name
        
    if "Candidates" in sheet_titles:
        return "Candidates"
        
    system_sheets = {"ActiveJobSheet", "CandidateAnalysis", "HRQuestions"}
    for title in sheet_titles:
        if title not in system_sheets:
            return title
            
    # Fallback if only system sheets exist (unlikely if user added data)
    return "Candidates"

def get_all_sheet_titles() -> List[str]:
    """
    Returns a list of all sheet titles in the spreadsheet.
    """
    try:
        service = get_service()
        spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        return [s['properties']['title'] for s in spreadsheet.get('sheets', [])]
    except Exception as e:
        print(f"❌ Error getting sheet titles: {e}")
        return []


# Global Cache for Job Descriptions
_JOB_CACHE = {
    "data": {},
    "timestamp": 0
}

def invalidate_job_cache():
    """Forces the job cache to expire."""
    _JOB_CACHE["timestamp"] = 0
    print("DEBUG: Job Cache Invalidated")

def get_all_job_descriptions():
    """
    Reads ActiveJobSheet and returns a dict mapping Job Title to JD details.
    Cached for 5 minutes (300 seconds) to improve performance.
    Now includes Status column (Column F).
    """
    import time
    
    # Check Cache
    current_time = time.time()
    if current_time - _JOB_CACHE["timestamp"] < 300:
        # print("DEBUG: Returning Cached Job Descriptions")
        return _JOB_CACHE["data"]

    try:
        # Read all data from ActiveJobSheet including Status column (F)
        rows = read_sheet("ActiveJobSheet!A:F")
        if not rows:
            return {}
        
        # Headers: Job Title, Job Description, Required Skills, Top Projects, Timestamp, Status
        # We try to identify columns by header name, or fallback to indices 0, 1, 2, 3, 4, 5
        headers = [h.strip().lower() for h in rows[0]]
        
        idx_title = -1
        idx_desc = -1
        idx_skills = -1
        idx_projects = -1
        idx_status = -1
        
        # Smart column finding
        for i, col in enumerate(headers):
            if "title" in col or "role" in col: idx_title = i
            elif "description" in col or "jd" in col: idx_desc = i
            elif "skills" in col: idx_skills = i
            elif "project" in col: idx_projects = i
            elif "status" in col: idx_status = i
            
        # Fallback to defaults if headers are weird or missing
        if idx_title == -1: idx_title = 0
        if idx_desc == -1: idx_desc = 1
        if idx_skills == -1: idx_skills = 2
        if idx_projects == -1: idx_projects = 3
        if idx_status == -1: idx_status = 5  # Column F
        
        jobs_map = {}
        for row in rows[1:]: # Skip header
            if len(row) <= idx_title: continue
            
            title = row[idx_title].strip()
            if not title: continue
            
            desc = row[idx_desc] if len(row) > idx_desc else ""
            skills = row[idx_skills] if len(row) > idx_skills else ""
            projects = row[idx_projects] if len(row) > idx_projects else ""
            # Status defaults to "Active" if not set
            status = row[idx_status].strip() if len(row) > idx_status and row[idx_status].strip() else "Active"
            
            jobs_map[title] = {
                "description": desc,
                "skills": skills,
                "top_projects": projects,
                "status": status
            }
        
        # Update Cache
        _JOB_CACHE["data"] = jobs_map
        _JOB_CACHE["timestamp"] = current_time
        print("DEBUG: Refreshed Job Description Cache")
            
        return jobs_map
    except Exception as e:
        print(f"❌ Error reading Job Descriptions: {e}")
        return {}

def update_job_status(job_title: str, status: str) -> bool:
    """
    Updates the Status column (Column F) for a specific job in ActiveJobSheet.
    Returns True if successful, False otherwise.
    """
    try:
        # Read all job data to find the row index
        rows = read_sheet("ActiveJobSheet!A:F")
        if not rows:
            return False
        
        # Find the row with matching job title (Column A)
        target_row_idx = -1
        for i, row in enumerate(rows):
            if i == 0:  # Skip header
                continue
            if row and row[0].strip().lower() == job_title.strip().lower():
                target_row_idx = i + 1  # Sheets are 1-indexed
                break
        
        if target_row_idx == -1:
            print(f"❌ Job '{job_title}' not found in ActiveJobSheet")
            return False
        
        # Update Column F (Status) for this row
        range_name = f"ActiveJobSheet!F{target_row_idx}"
        write_to_sheet(range_name, [[status]])
        
        # Invalidate cache so next fetch gets fresh data
        invalidate_job_cache()
        
        print(f"✅ Updated status for '{job_title}' to '{status}'")
        return True
        
    except Exception as e:
        print(f"❌ Error updating job status: {e}")
        return False

def get_all_job_titles():
    """
    Optimized fetch: Reads ONLY the first column of ActiveJobSheet to get titles.
    Much faster than reading the whole sheet.
    """
    try:
        # Read only Column A (Titles)
        rows = read_sheet("ActiveJobSheet!A:A")
        if not rows: return []
        
        # ActiveJobSheet always has a header row (e.g., "Job Title")
        # We start from index 1 to skip it.
        # We also filter out any potential empty or header-like leftovers just in case.
        start_idx = 1 
        
        titles = []
        for r in rows[start_idx:]:
            if r and r[0].strip():
                val = r[0].strip()
                # Extra safety: ignore if it looks like a header
                if val.lower() in ["job title", "job name", "role", "title"]:
                    continue
                titles.append(val)
                
        return sorted(list(set(titles))) # Deduplicate and sort
    except Exception as e:
        print(f"❌ Error reading Job Titles: {e}")
        return []

def get_candidate_name_by_email(job_title, email):
    """
    Looks up Candidate Name using Email in 'Analysis - {JobTitle}' sheet.
    """
    try:
        sheet_name = f"Analysis - {job_title}"
        rows = read_sheet(f"{sheet_name}!A:K")
        if not rows: return None
        
        # Email is in Column C (index 2), Name in Column E (index 4)
        # Headers are in row 0, data starts row 1
        
        target_email = email.lower().strip()
        
        for row in rows[1:]:
            if len(row) > 2:
                row_email = row[2].lower().strip()
                if row_email == target_email:
                    return row[4].strip() if len(row) > 4 else "Unknown" # Name
                    
        return None
    except Exception as e:
        print(f"❌ Error finding name for {email}: {e}")
        return None

def get_questions_by_name(job_title, candidate_name):
    """
    Looks up Recommended Questions in 'HRQuestions' sheet.
    Matches both Name and Job Title to be safe.
    """
    try:
        rows = read_sheet("HRQuestions!A:E")
        if not rows: return None
        
        # Schema: Date, Name, Job, ResumeLink, Questions
        # Indices: 1, 2, 4
        
        target_name = candidate_name.lower().strip()
        target_job = job_title.lower().strip()
        
        for row in rows[1:]:
            if len(row) > 4:
                row_name = row[1].lower().strip()
                row_job = row[2].lower().strip()
                
                # Check match (Job + Name)
                if row_name == target_name and row_job == target_job:
                    return row[4] # The questions string
        
        return None
    except Exception as e:
        print(f"❌ Error finding questions for {candidate_name}: {e}")
        return None
