from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel
from typing import List, Optional
from langgraph_flows.graph import hr_pipeline_graph
from langgraph_flows.nodes import extract_jd_requirements_node
from services.sheets import read_sheet, write_to_sheet

router = APIRouter()

class JDSubmission(BaseModel):
    jd_text: str

class CandidateData(BaseModel):
    source: str
    date: str
    name: str
    email: str
    qualification: str
    current_position: str
    experience: str
    resume_url: str
    job_applied: str

from services.sheets import read_sheet, write_to_sheet, ensure_sheet_exists, get_source_sheet_name, append_to_sheet, invalidate_job_cache
from services.drive_service import list_files_in_folder, download_file
from services.resume_parser import parse_resume, parse_resumes_batch
import os
import datetime

@router.post("/submit-jd")
def submit_jd(jd: JDSubmission):
    # Enforce Headers for ActiveJobSheet
    ensure_sheet_exists("ActiveJobSheet")
    write_to_sheet("ActiveJobSheet!A1:E1", [["Job Title", "Description", "Required Skills", "Top Projects Reference", "Timestamp"]])
    
    result = extract_jd_requirements_node({"jd_text": jd.jd_text})
    
    # Invalidate cache so new job appears immediately
    invalidate_job_cache()
    
    return result

# GLOBAL CACHE for existing identities per sheet to avoid repeated API calls
# Map: SheetName -> {'identities': Set((name, contact)), 'sources': Set(source_string)}
GLOBAL_SHEET_CACHE = {}

def get_sheet_data(sheet_name):
    from services.sheets import ensure_sheet_exists    
    if sheet_name in GLOBAL_SHEET_CACHE:
        return GLOBAL_SHEET_CACHE[sheet_name]
    
    CANDIDATE_HEADERS = [
        "Source", "Date", "Name", "Contact", "Qualification", 
        "Current Position", "Experience", "Skills", "Top Projects",
        "Job Applied For", "Resume Link"
    ]
    
    ensure_sheet_exists(sheet_name, CANDIDATE_HEADERS)
    
    # Read existing (Column A for Source, C for Name, D for Contact)
    rows = read_sheet(f"{sheet_name}!A:D")
    identities = set()
    sources = set()
    dates_map = {} # Name -> DateStr
    
    if rows:
        for r in rows[1:]: # Skip header
            # Source is Col 0
            if len(r) > 0: sources.add(r[0].strip())
            
            # Date is Col 1
            if len(r) > 1:
                d_val = r[1].strip()
            else:
                d_val = ""

            # Identity
            name = r[2].strip().lower() if len(r) > 2 else ""
            contact = r[3].strip() if len(r) > 3 else ""
            if name:
                identities.add((name, contact))
                if d_val: dates_map[name] = d_val
    
    data = {'identities': identities, 'sources': sources, 'dates': dates_map}
    GLOBAL_SHEET_CACHE[sheet_name] = data
    return data
    
@router.post("/import-from-drive")
def import_from_drive(
    job_title_filter: Optional[str] = None,
    time_period: Optional[str] = Query(None, description="Time period filter: ALL, LAST_7_DAYS, LAST_30_DAYS, CUSTOM"),
    start_date: Optional[str] = Query(None, description="Start date in YYYY-MM-DD format"),
    end_date: Optional[str] = Query(None, description="End date in YYYY-MM-DD format")
):
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    if not folder_id:
        raise HTTPException(status_code=500, detail="GOOGLE_DRIVE_FOLDER_ID not set")
    
    # Calculate min_date and max_date based on time_period and provided dates
    min_date = None
    max_date = None
    
    if time_period and time_period != "ALL":
        today = datetime.date.today()
        if time_period == "LAST_7_DAYS":
            computed_start = today - datetime.timedelta(days=7)
            min_date = computed_start.isoformat()
            max_date = today.isoformat()
        elif time_period == "LAST_30_DAYS":
            computed_start = today - datetime.timedelta(days=30)
            min_date = computed_start.isoformat()
            max_date = today.isoformat()
        elif (time_period.startswith("CUSTOM") or time_period == "CUSTOM") and start_date:
            # CUSTOM_SINGLE or CUSTOM_RANGE use explicit start/end dates
            # Validate date format
            try:
                datetime.datetime.strptime(start_date, '%Y-%m-%d')
                min_date = start_date
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")
            
            if end_date:
                try:
                    datetime.datetime.strptime(end_date, '%Y-%m-%d')
                    max_date = end_date
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")

    # Clear cache to ensure fresh duplicate check
    GLOBAL_SHEET_CACHE.clear()

    imported_count = 0
    skipped_files_count = 0
    errors = []
    
    # NEW: Folder-Based Iteration
    from services.drive_service import list_folders, list_files_recursive
    from services.sheets import get_all_job_descriptions
    
    # ... (Keep existing prompt logic) ... 
    # [Lines 83-181 remain same, but for brevity I must include them or skip them carefully]
    # To avoid re-pasting 100 lines, I will assume the prompt logic is unchanged and focus on the loop.
    # WAIT: The replace_file_content tool needs specific target. 
    # I will replace the helper function and then the loop logic. 
    # But `import_from_drive` is big. I should probably replace the helper first, then the loop.
    # Actually, I'll rewrite the helper `get_sheet_identities` to `get_sheet_data` 
    # and then update the usage in `process_batch` and the main loop.
    
    # Let's do it in chunks. 
    # Chunk 1: The Helper Function
    
    # ...


    imported_count = 0
    errors = []
    
    # NEW: Folder-Based Iteration
    from services.drive_service import list_folders, list_files_recursive
    from services.sheets import get_all_job_descriptions
    
    # Get all valid JDs to validate folder names against
    valid_jobs_map = get_all_job_descriptions()
    valid_job_titles = set(valid_jobs_map.keys())
    
    # 1. List all folders in Root
    folders = list_folders(folder_id)
    print(f"DEBUG: Found {len(folders)} folders in Drive: {[f['name'] for f in folders]}")
    
    if not folders:
        print("DEBUG: No subfolders found. Checking root...")
        folders = [{"id": folder_id, "name": "General Application"}]
        
    
    # NEW: Semantic Folder Matching
    semantic_matches = []
    
    if job_title_filter:
        print(f"DEBUG: Using Semantic Matching for '{job_title_filter}' across {len(folders)} folders...")
        from services.llm import get_llm
        from langchain_core.prompts import PromptTemplate
        from langchain_core.output_parsers import JsonOutputParser
        import json
        
        folder_names = [f['name'] for f in folders]
        
        matcher_prompt = """You are an intelligent HR folder matching assistant.
        User is searching for resumes for the role: "{job_title}".
        
        Your task: Select the SINGLE BEST matching folder from the list below that would likely contain relevant resumes.
        
        MATCHING RULES (in order of priority):
        1. **Exact Match**: If a folder name contains the exact job title, return it (e.g., "HR Assistant" → "HR Assistant Feb 2024")
        2. **Semantic Match**: Consider semantically similar roles:
           - "HR Assistant" matches "HR Executive", "HR Coordinator", "HR Specialist"
           - "Software Engineer" matches "Backend Engineer", "Sr Software Developer", "Implementation Engineer"
           - "Account Executive" matches "Accounts Executive", "Senior Accountant"
        3. **Hierarchical Match**: Include senior/junior variations (e.g., "Engineer" can match "Sr Engineer" or "Associate Engineer")
        4. **Avoid Generic Folders**: Skip folders like "General", "Archive", "Invoices"
        5. **Most Recent First**: If multiple similar folders exist, prefer the most recent one based on date in folder name
        
        Folders Available:
        {folders_list}
        
        Return ONLY a JSON list with THE SINGLE BEST matching folder name.
        Example: ["HR Executive Dec 2024 / OCT 2025"]
        
        CRITICAL: Return exactly ONE folder name (the best match). Do NOT return multiple folders.
        If NO folders are semantically related, return an empty list: []
        """
        
        try:
            llm = get_llm()
            parser = JsonOutputParser()
            chain = PromptTemplate(template=matcher_prompt, input_variables=["job_title", "folders_list"]) | llm | parser
            
            # Run LLM
            matched_names = chain.invoke({"job_title": job_title_filter, "folders_list": json.dumps(folder_names)})
            
            if matched_names and isinstance(matched_names, list) and len(matched_names) > 0:
                print(f"✅ Semantic Match Found: {matched_names}")
                semantic_matches = matched_names
                # CRITICAL FIX: Update the main folders list to ONLY contain the matches!
                folders = [f for f in folders if f['name'] in semantic_matches]
            else:
                print(f"⚠️ No semantic matches found for '{job_title_filter}'. Falling back to strict keyword search.")
                # Fallback: Use keyword matching
                job_keywords = set(job_title_filter.lower().split())
                matched_folders = []
                for folder in folders:
                    folder_keywords = set(folder['name'].lower().split())
                    overlap = job_keywords & folder_keywords
                    overlap_ratio = len(overlap) / len(job_keywords) if job_keywords else 0
                    # Require at least 50% keyword overlap
                    if overlap_ratio >= 0.5:
                        matched_folders.append(folder)
                        print(f"   ✓ Keyword match: {folder['name']} (overlap: {overlap})")
                
                if matched_folders:
                    folders = matched_folders
                    print(f"✅ Keyword Search found {len(folders)} folders")
                else:
                    print(f"❌ No folders matched '{job_title_filter}'. Aborting import.")
                    return {"message": f"No folders found matching '{job_title_filter}'", "errors": [], "scanned_folders": []}
                
        except Exception as e:
            print(f"⚠️ Semantic Logic Failed: {e}. Falling back to strict search.")
            # Same fallback logic
            job_keywords = set(job_title_filter.lower().split())
            matched_folders = []
            for folder in folders:
                folder_keywords = set(folder['name'].lower().split())
                overlap = job_keywords & folder_keywords
                overlap_ratio = len(overlap) / len(job_keywords) if job_keywords else 0
                if overlap_ratio >= 0.5:
                    matched_folders.append(folder)
            if matched_folders:
                folders = matched_folders
            else:
                return {"message": f"No folders found matching '{job_title_filter}'", "errors": [], "scanned_folders": []} 
    
    # BATCHING LOGIC
    BATCH_SIZE = 10
    batch_buffer = [] # Stores dicts: {'content': bytes, 'filename': str, 'source_key': str, 'job_title': str, 'file_obj': dict}

    def process_batch(buffer_list, errors_list):
        if not buffer_list: return 0
        
        # 1. Extract texts from files (CPU bound, fast-ish)
        from services.pdf import extract_text_from_pdf
        from services.docx_parser import extract_text_from_docx
        import re

        texts_payload = [] # (filename, text)
        valid_items = []   # items that successfully extracted text

        for item in buffer_list:
            fname = item['filename']
            content = item['content']
            text = ""
            try:
                if fname.lower().endswith(".pdf"):
                    text = extract_text_from_pdf(content)
                elif fname.lower().endswith(".docx"):
                    text = extract_text_from_docx(content)
                else:
                    try: text = content.decode('utf-8')
                    except: pass
                
                if text:
                    text = re.sub(r'\s+', ' ', text).strip()
                
                if text and len(text) > 50:
                    texts_payload.append((fname, text))
                    valid_items.append(item)
                else:
                    errors_list.append(f"{fname}: Empty/Unreadable text")
            except Exception as ex:
                errors_list.append(f"{fname}: Extraction Error - {ex}")

        if not texts_payload: 
            print(f"⚠️ Batch had no valid text extracted from {len(buffer_list)} files")
            return 0


        # 2. Call Batch LLM
        print(f"🤖 Sending {len(texts_payload)} resumes to LLM for parsing...")
        import sys
        sys.stdout.flush() 
        
        parsed_results = parse_resumes_batch(texts_payload)
        
        print(f"✅ LLM returned {len(parsed_results)} parsed results")
        
        processed_count = 0
        
        # Group rows by Target Sheet (Job Title)
        from collections import defaultdict
        rows_by_sheet = defaultdict(list)
        
        for idx, item in enumerate(valid_items):
            if idx < len(parsed_results):
                data = parsed_results[idx]
                target_job_sheet = item['job_title']
                
                # Check Duplicates in THAT specific sheet (Identity Check)
                sheet_data = get_sheet_data(target_job_sheet)
                existing_identities = sheet_data['identities']
                
                name = data.get("Name", "Unknown").strip()
                contact = data.get("Contact", "").strip()
                identity = (name.lower(), contact)
                
                if identity in existing_identities:
                        print(f"⏭️ Duplicate Candidate Skipped in '{target_job_sheet}': {name}")
                        continue
                        
                # Add to cache immediately
                existing_identities.add(identity)
                
                # DATE EXTRACTION
                # Use file createdTime if available, else today
                file_date = datetime.date.today().isoformat()
                file_obj = item.get('file_obj', {})
                # Use modifiedTime if available (User Preference), else createdTime
                date_src = file_obj.get('modifiedTime', file_obj.get('createdTime'))
                resume_link_val = file_obj.get('webViewLink', "N/A")
                if date_src:
                    # Drive returns e.g., "2023-10-27T10:00:00.000Z"
                    try:
                        file_date = date_src.split("T")[0]
                    except:
                        pass
                
                row = [
                    item['source_key'],
                    file_date, # Use Actual Created Date
                    name,
                    f"'{contact}", 
                    data.get("Qualification", ""),
                    data.get("Current_Position", ""),
                    data.get("Experience", ""),
                    data.get("Skills", ""),
                    data.get("Top_Projects", ""),
                    target_job_sheet, # Job Applied For
                    resume_link_val
                ]
                rows_by_sheet[target_job_sheet].append(row)
                processed_count += 1
            else:
                errors_list.append(f"{item['filename']}: LLM returned fewer results than inputs")

        print(f"📊 Batch Summary: {processed_count} new candidates")
        
        # Write to respective sheets with GATEKEEPER DEDUPLICATION
        for sheet_name, rows in rows_by_sheet.items():
            if rows:
                print(f"📝 Preparing to write {len(rows)} rows to sheet '{sheet_name}'...")
                try:
                    # 1. READ CURRENT STATE (Gatekeeper)
                    # We fetch A (Source) and C (Name) to double-check uniqueness before writing.
                    # This handles cases where parallel imports might have written to the sheet 
                    # OR if existing redundancy exists that the initial cache didn't catch due to restart.
                    ensure_sheet_exists(sheet_name)
                    current_data = read_sheet(f"{sheet_name}!A:C")
                    
                    existing_sources = set()
                    existing_names = set()
                    
                    if current_data:
                         for r in current_data:
                             if len(r) > 0: existing_sources.add(r[0].strip())
                             if len(r) > 2: existing_names.add(r[2].strip().lower())

                    # 2. FILTER ROWS
                    unique_rows = []
                    duplicates_skipped = 0
                    
                    for r in rows:
                        s_key = r[0] # Source
                        n_key = r[2].strip().lower() # Name
                        
                        # Strict Check: If Source exists OR Name exists, SKIP.
                        # Name check is crucial for "Same person, slightly different file/contact"
                        if s_key in existing_sources:
                            print(f"DEBUG: Gatekeeper skipped Source Match: {s_key}")
                            duplicates_skipped += 1
                            continue
                        
                        if n_key in existing_names:
                            print(f"DEBUG: Gatekeeper skipped Name Match: {n_key}")
                            duplicates_skipped += 1
                            continue
                        
                        unique_rows.append(r)
                        # Add to local temporary set to prevent duplicates WITHIN the same batch being written
                        existing_names.add(n_key) 
                        existing_sources.add(s_key)

                    # 3. WRITE IF UNIQUE
                    if unique_rows:
                        append_to_sheet(sheet_name, unique_rows)
                        
                        # Update Global Cache
                        if sheet_name in GLOBAL_SHEET_CACHE:
                             new_sources = {r[0] for r in unique_rows}
                             GLOBAL_SHEET_CACHE[sheet_name]['sources'].update(new_sources)
                             print(f"DEBUG: Updated cache for '{sheet_name}' with {len(new_sources)} new sources (Global)")
                             
                        print(f"✅ Successfully wrote {len(unique_rows)} unique rows to {sheet_name} (Skipped {duplicates_skipped} duplicates)")
                    else:
                        print(f"⚠️ All {len(rows)} candidates in this batch were duplicates. Zero writes.")
                        skipped_files_count += len(rows) # Count these as skipped for stats

                except Exception as sheet_err:
                    print(f"❌ SHEET WRITE FAILED for {sheet_name}: {sheet_err}")
                    errors_list.append(f"Sheet write error ({sheet_name}): {sheet_err}")
        
        return processed_count

    # Loop through folders
    for folder in folders:
        folder_name = folder['name'].strip()
        
        canonical_job_title = folder_name
        # Simplified Tagging
        if job_title_filter:
             canonical_job_title = job_title_filter
        else:
             for valid_job in valid_job_titles:
                 if valid_job.lower() in folder_name.lower():
                     canonical_job_title = valid_job
                     break
        
        if min_date:
            filter_msg = f"{min_date} to {max_date or 'NOW'}"
        else:
            filter_msg = 'ALL TIME'
            
        print(f"📂 Scanning Folder: {folder_name} (Target Sheet: {canonical_job_title}) WITH FILTER: {filter_msg}")

        try:
            # Pass MIN_DATE and MAX_DATE to list_files
            files = list_files_recursive(folder['id'], min_date=min_date, max_date=max_date)
            print(f"DEBUG: Recursive scan found {len(files)} files in folder '{folder_name}' matching filter")
            
            for f in files:
                source_key = f"Drive: {f['name']}"
                
                # PRE-CHECK: Source Duplication (Optimization)
                # Ensure we have the data for this sheet
                # Ensure we have the data for this sheet
                sheet_data = get_sheet_data(canonical_job_title)
                
                if source_key in sheet_data['sources']:
                     print(f"DEBUG: Skipping duplicate {f['name']}")
                     skipped_files_count += 1
                     continue

                try:
                    print(f"DEBUG: Downloading {f['name']}...")
                    content = download_file(f['id'])
                    
                    parser_filename = f['name']
                    if '.' not in parser_filename:
                        parser_filename += ".docx" 

                    batch_buffer.append({
                        'content': content, 
                        'filename': parser_filename, 
                        'source_key': source_key,
                        'job_title': canonical_job_title,
                        'file_obj': f
                    })
                    print(f"DEBUG: Added {f['name']} to buffer. Size: {len(batch_buffer)}")

                    if len(batch_buffer) >= BATCH_SIZE:
                        print(f"🔄 Processing Batch (Files {imported_count + 1}-{imported_count + len(batch_buffer)})...")
                        cnt = process_batch(batch_buffer, errors)
                        imported_count += cnt
                        print(f"✅ Batch Complete! Total Imported So Far: {imported_count}")
                        batch_buffer = []
                    
                except Exception as e:
                    print(f"❌ Error processing {f['name']}: {e}")
                    errors.append(f"{f['name']}: Download Error - {str(e)}")
            
            # Process remaining in folder
            if batch_buffer:
                cnt = process_batch(batch_buffer, errors)
                imported_count += cnt
                batch_buffer = []
                
        except Exception as folder_err:
             print(f"❌ Error scanning folder {folder_name}: {folder_err}")
             errors.append(f"Folder Access Error: {folder_name}")

    return {
        "message": f"Imported {imported_count} candidates.", 
        "errors": errors, 
        "scanned_folders": [f['name'] for f in folders],
        "stats": {
            "imported": imported_count,
            "skipped_existing_files": skipped_files_count,
            "scanned_folders_count": len(folders)
        }
    }

@router.post("/trigger-candidate-sync")
def trigger_sync(background_tasks: BackgroundTasks, job_filter: Optional[str] = None, time_period: Optional[str] = "ALL", custom_date: Optional[str] = None):
    # Enforce Headers for ALL Output Sheets
    ensure_sheet_exists("ActiveJobSheet")
    write_to_sheet("ActiveJobSheet!A1:B1", [["Timestamp", "Requirements JSON"]])
    
    ensure_sheet_exists("HRQuestions")
    # UPDATED HEADER: Added Date and Resume Link
    write_to_sheet("HRQuestions!A1:E1", [["Date", "Candidate Name", "Job", "Resume Link", "Questions"]])

    # Fetch ALL JDs into a map
    from services.sheets import get_all_job_descriptions
    all_jobs_map = get_all_job_descriptions()
    
    # Determine Source Sheet(s)
    source_sheets_to_process = []
    
    # Also determine which Analysis Sheet to check for duplicates
    processed_names = set()
    
    if job_filter:
        source_sheets_to_process.append(job_filter)
        
        # Load processed candidates (to avoid re-analyzing)
        analysis_sheet_target = f"Analysis - {job_filter}"
        ensure_sheet_exists(analysis_sheet_target, ["Candidate Name", "Match Score", "Strengths", "Weaknesses", "Experience Check", "Skill Match", "Verdict", "Timestamp", "Job Applied For"])
        processed_rows = read_sheet(f"{analysis_sheet_target}!A:A")
        if processed_rows and len(processed_rows) > 1:
             processed_names = {r[0] for r in processed_rows[1:]}
        print(f"DEBUG: Found {len(processed_names)} already processed candidates in '{analysis_sheet_target}'")
        
    else:
        source_sheets_to_process.append("Candidates")
        for j in all_jobs_map.keys():
             source_sheets_to_process.append(j)

    print(f"DEBUG: Will sync candidates from sheets: {source_sheets_to_process}")

    triggered_count = 0
    processed_identities_this_run = set()
    
    # CALCULATE MIN DATE FOR PROCESSING
    min_date_obj = None
    today = datetime.date.today()
    if time_period == "LAST_7_DAYS":
        min_date_obj = today - datetime.timedelta(days=7)
    elif time_period == "LAST_30_DAYS":
        min_date_obj = today - datetime.timedelta(days=30)
    elif time_period == "CUSTOM" and custom_date:
        try:
            min_date_obj = datetime.date.fromisoformat(custom_date)
        except: pass
    
    print(f"DEBUG: Sync Filter - Period: {time_period}, Min Date: {min_date_obj}")

    for source_name in source_sheets_to_process:
        rows = read_sheet(f"{source_name}!A:K", value_render_option='FORMULA') 
        if not rows: continue
        
        # Header Detection
        data_rows = rows
        if rows and str(rows[0][0]).lower() == "source":
            data_rows = rows[1:]

        for row in data_rows:
            if len(row) < 3: continue 
            
            get_col = lambda idx: row[idx] if len(row) > idx else "N/A"
            resume_link = get_col(10) # Index 10 is Resume Link
            
            # --- DATE FILTERING ---
            # STRICT DATE FILTERING
            # Date is at index 1
            row_date_str = get_col(1)
            
            if min_date_obj:
                # If Strict Filter is on, we MUST have a valid date
                if not row_date_str or row_date_str == "N/A":
                    # No date => Skip
                    continue
                
                try:
                    # Handle Excel serial date (Google Sheets may return dates as numbers)
                    if isinstance(row_date_str, (int, float)):
                        # Convert Excel serial date to Python date
                        # Excel dates are days since December 30, 1899
                        base_date = datetime.date(1899, 12, 30)
                        row_date = base_date + datetime.timedelta(days=int(row_date_str))
                        print(f"DEBUG: Converted serial date {row_date_str} to {row_date}")
                    else:
                        # Regular string date parsing
                        row_date = datetime.date.fromisoformat(str(row_date_str).strip())
                    
                    if row_date < min_date_obj:
                         # Skip old candidates
                         print(f"DEBUG: Skipping candidate {get_col(2)} - date {row_date} < {min_date_obj}")
                         continue
                    else:
                         print(f"DEBUG: Including candidate {get_col(2)} - date {row_date} >= {min_date_obj}")
                except Exception as e:
                    # Parse Error => Skip (Strict)
                    print(f"DEBUG: Strictly skipping due to date parse error for '{row_date_str}': {e}")
                    continue
            
            name = get_col(2)
            if not name: continue
            
            if isinstance(name, str) and name.startswith("="): name = name[1:]
            
            if job_filter and name in processed_names: 
                continue
                
            if name in processed_identities_this_run:
                continue

            processed_identities_this_run.add(name)

            contact = get_col(3)
            if isinstance(contact, str) and contact.startswith("="): contact = contact[1:]
            
            raw_job_title = str(get_col(9)).strip()
            if (raw_job_title == "N/A" or not raw_job_title) and source_name not in ["Candidates", "Sheet1"]:
                 raw_job_title = source_name
            if raw_job_title == "N/A" or not raw_job_title: 
                raw_job_title = "Unknown"
            
            # Lookup JD
            jd_context = {}
            matched_title = "Unknown"
            
            if raw_job_title in all_jobs_map:
                jd_context = all_jobs_map[raw_job_title]
                matched_title = raw_job_title
            else:
                found_key = next((k for k in all_jobs_map if k.lower() == raw_job_title.lower()), None)
                if found_key:
                    jd_context = all_jobs_map[found_key]
                    matched_title = found_key
                else:
                    found_key = next((k for k in all_jobs_map if raw_job_title.lower() in k.lower() or k.lower() in raw_job_title.lower()), None)
                    if found_key:
                        jd_context = all_jobs_map[found_key]
                        matched_title = found_key

            if job_filter:
                if matched_title.lower() != job_filter.strip().lower():
                    continue
            
            c_data = {
                "Source": get_col(0),
                "Date": row_date_str, # Keep original string
                "Name": name,
                "Contact": contact,
                "Qualification": get_col(4),
                "Current Position": get_col(5),
                "Experience": get_col(6),
                "Skills": get_col(7),      
                "Top Projects": get_col(8),
                "Job Applied For": matched_title
            }
            
            resume_text = f"""
            Name: {c_data['Name']}
            Contact: {c_data['Contact']}
            Qualification: {c_data['Qualification']}
            Current Position: {c_data['Current Position']}
            Experience: {c_data['Experience']}
            Skills: {c_data['Skills']}
            Top Projects: {c_data['Top Projects']}
            """

            initial_state = {
                "candidate_data": c_data,
                "jd_requirements": jd_context, 
                "resume_text": resume_text,
                "resume_url": resume_link
            }
            
            print(f"DEBUG: Queuing Analysis for '{name}' -> '{matched_title}'")
            background_tasks.add_task(hr_pipeline_graph.invoke, initial_state)
            triggered_count += 1
            
    skipped_count = len(processed_names) if job_filter else 0 
    
    return {
        "message": f"Triggered processing for {triggered_count} new candidates across {len(all_jobs_map)} defined jobs.",
        "stats": {
            "triggered": triggered_count,
            "skipped": skipped_count,
            "job_count": len(all_jobs_map)
        }
    }

@router.get("/candidates")
def get_candidates(job_title: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None):
    # Filter by Job and Date Range
    
    if not job_title:
        return []
    
    target_sheet = f"Analysis - {job_title}"
    
    ANALYSIS_HEADERS = [
        "Candidate Name", "Match Score", "Strengths", "Weaknesses", 
        "Experience Check", "Skill Match", "Verdict", "Timestamp", 
        "Job Applied For", "Email", "Contact"
    ]
    
    ensure_sheet_exists(target_sheet, ANALYSIS_HEADERS)
    
    rows = read_sheet(f"{target_sheet}!A:K")
    if not rows: return []
    
    # --- HYDRATION LOGIC START ---
    contact_map = {}
    date_map = {}
    try:
        source_data = get_sheet_data(job_title) 
        if source_data:
            if 'identities' in source_data:
                for name, contact in source_data['identities']:
                    if name:
                        contact_map[name.lower()] = contact
            if 'dates' in source_data:
                date_map = source_data['dates']
    except Exception as e:
        print(f"⚠️ Warning: Failed to hydrate contact/date info for job '{job_title}': {e}")
    # --- HYDRATION LOGIC END ---

    headers = rows[0]
    data = []
    
    # Pre-process dates if needed
    start_dt = datetime.date.fromisoformat(start_date) if start_date else None
    end_dt = datetime.date.fromisoformat(end_date) if end_date else None

    for r in rows[1:]:
        if len(r) < len(headers):
             r = r + [""] * (len(headers) - len(r))
        item = {h: val for h, val in zip(headers, r)}
        
        # DATE FILTER
        # Analysis Date is item['Timestamp']
        # Format usually is ISO or human readable? Current implementation writes Today's Date.
        # Let's assume ISO YYYY-MM-DD
        if start_dt or end_dt:
            keep_row = True
            try:
                # STRATEGY: Prefer "Application Date" (from Source Sheet) -> "Processing Date" (Timestamp)
                # This aligns Analysis tabs with Import tab filtering.
                
                c_name = item.get("Candidate Name", "").strip().lower()
                date_val_obj = None
                
                # 1. Try Source Date
                raw_date = date_map.get(c_name)
                
                # 2. Fallback to Timestamp
                if not raw_date or raw_date == "N/A":
                    raw_date = item.get("Timestamp", "")
                
                if not raw_date or raw_date == "N/A":
                     keep_row = False # Strict: Missing Date = Hide
                else:
                    # Parse (Excel or String)
                    if isinstance(raw_date, (int, float)):
                         base_date = datetime.date(1899, 12, 30)
                         date_val_obj = base_date + datetime.timedelta(days=int(raw_date))
                    else:
                         # Handle "YYYY-MM-DD HH:MM:SS" or "YYYY-MM-DD"
                         clean_ts = str(raw_date).replace("T", " ").split(" ")[0].strip()
                         date_val_obj = datetime.date.fromisoformat(clean_ts)
                    
                    if start_dt and date_val_obj < start_dt: keep_row = False
                    if end_dt and date_val_obj > end_dt: keep_row = False
            except Exception as e:
                # print(f"Date Filter Error {item.get('Candidate Name')}: {e}")
                keep_row = False # Parse Fail = Hide (Strict)
            
            if not keep_row: continue

        # Hydration Fallback
        if not item.get("Email") or not item.get("Contact"):
            c_name = item.get("Candidate Name", "").strip()
            contact_info = contact_map.get(c_name.lower(), "")
            
            if not item.get("Contact"):
                 item["Contact"] = contact_info
            
            if not item.get("Email"):
                import re
                email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', contact_info)
                item["Email"] = email_match.group(0) if email_match else ""

        data.append(item)
    return data

@router.get("/candidates/imported")
def get_imported_candidates(job_title: str, start_date: Optional[str] = None, end_date: Optional[str] = None):
    """
    Fetch RAW imported candidates from source sheet (not analyzed).
    """
    from services.sheets import read_sheet
    
    source_sheet = f"{job_title}"
    
    try:
        rows = read_sheet(f"{source_sheet}!A:D")
        
        if not rows or len(rows) < 2:
            return []
        
        headers = rows[0]
        data = []
        
        start_dt = datetime.date.fromisoformat(start_date) if start_date else None
        end_dt = datetime.date.fromisoformat(end_date) if end_date else None

        for r in rows[1:]:
            if len(r) < len(headers):
                r = r + [""] * (len(headers) - len(r))
            item = {h: val for h, val in zip(headers, r)}
            
            # STRICT DATE FILTER (Index 1)
            keep_row = True
            if start_dt or end_dt:
                # Safer: Use Index 1 directly instead of relying on header name "Date"
                item_date_str = r[1] if len(r) > 1 else ""
                
                if not item_date_str or item_date_str in ["N/A", ""]:
                     keep_row = False # Strict: No date = No match
                else:
                     try:
                         item_date = None
                         if isinstance(item_date_str, (int, float)):
                             # Excel Serial
                             row_date = datetime.date(1899, 12, 30) + datetime.timedelta(days=int(item_date_str))
                             item_date = row_date
                         else:
                             # String
                             clean = str(item_date_str).split("T")[0].strip()
                             item_date = datetime.date.fromisoformat(clean)
                         
                         if start_dt and item_date < start_dt: keep_row = False
                         if end_dt and item_date > end_dt: keep_row = False
                     except:
                         keep_row = False # Parse failure = No match
            
            if keep_row:
                data.append(item)
        
        return data
    except Exception as e:
        print(f"Error fetching imported candidates: {e}")
        return []

@router.get("/questions/{candidate_name}")
def get_questions(candidate_name: str):
    ensure_sheet_exists("HRQuestions", ["Date", "Candidate Name", "Job", "Resume Link", "Questions"])
    rows = read_sheet("HRQuestions!A:E")

    if not rows: return {"questions": []}
    
    # Skip header row
    for r in rows[1:]:
        # Data format: Date (0), Candidate Name (1), Job (2), Resume Link (3), Questions (4)
        if len(r) > 4 and r[1] == candidate_name:
            return {
                "candidate": r[1],
                "job": r[2],
                "resume_link": r[3],
                "questions": r[4].split("\n") if r[4] else []
            }
    return {"questions": []}

@router.get("/jobs")
def get_jobs():
    """
    Fetch all available job titles from ActiveJobSheet.
    Optimized to fetch ONLY titles (Column A) and cached for 60 seconds.
    """
    from services.sheets import get_all_job_titles
    import time

    # PROPER CACHING IMPLEMENTATION
    current_time = time.time()
    
    # Use a global variable for simple in-memory caching
    # (Note: In a production app with multiple workers, this cache is per-worker, which is fine here)
    if not hasattr(get_jobs, "cache"):
        get_jobs.cache = {"data": [], "timestamp": 0}
    
    # Check Cache (TTL 60 seconds)
    if current_time - get_jobs.cache["timestamp"] < 60:
        # print("DEBUG: Serving Jobs from Cache")
        return get_jobs.cache["data"]

    ensure_sheet_exists("ActiveJobSheet")
    
    # Use the optimized function
    titles = get_all_job_titles()
    
    # Update Cache
    get_jobs.cache = {"data": titles, "timestamp": current_time}
    print("DEBUG: Fetched & Cached Job Titles from Sheets")
    
    return titles

class InterviewRequest(BaseModel):
    candidate_name: str
    candidate_email: str
    job_title: str
    date: Optional[str] = None # YYYY-MM-DD
    time: Optional[str] = None # HH:MM

@router.post("/schedule-interview")
async def manual_schedule_interview(req: InterviewRequest):
    print(f"📅 Manual Invite Request: {req.candidate_name} ({req.candidate_email}) for {req.job_title} at {req.date} {req.time}")
    
    # Validation
    if not req.candidate_email or "@" not in req.candidate_email:
        raise HTTPException(status_code=400, detail="Valid email address is required.")

    try:
        from services.calendar_service import schedule_interview
        result = schedule_interview(
            req.candidate_name, 
            req.candidate_email, 
            req.job_title,
            fixed_date=req.date,
            fixed_time=req.time
        )
        
        if "Error" in result or "Failed" in result:
             raise HTTPException(status_code=500, detail=result)
             
        return {"status": "success", "message": result}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scheduling failed: {str(e)}")

@router.post("/schedule-interview/batch")
async def batch_schedule_interview(reqs: List[InterviewRequest]):
    print(f"📅 BATCH Invite Request: {len(reqs)} candidates")
    
    results = []
    
    # Process sequentially to avoid calendar rate limits
    from services.calendar_service import schedule_interview
    
    for r in reqs:
        # Check email validity
        if not r.candidate_email or "@" not in r.candidate_email:
             results.append({"name": r.candidate_name, "status": "failed", "error": "Missing Email"})
             continue
             
        try:
             res = schedule_interview(r.candidate_name, r.candidate_email, r.job_title)
             if "Error" in res or "Failed" in res:
                  results.append({"name": r.candidate_name, "status": "failed", "error": res})
             else:
                  results.append({"name": r.candidate_name, "status": "success", "info": res})
                  
        except Exception as e:
             results.append({"name": r.candidate_name, "status": "failed", "error": str(e)})
             
    return {"status": "completed", "results": results}

@router.get("/jobs/details")
def get_job_details():
    """
    Fetch ALL Job Descriptions with full details (Skills, Experience, etc.)
    """
    from services.sheets import get_all_job_descriptions
    
    try:
        jobs_map = get_all_job_descriptions()
        
        # Convert dict to list for frontend
        jobs_list = []
        for title, details in jobs_map.items():
            jobs_list.append({
                "job_title": title,
                "description": details.get("description", ""),
                "skills": details.get("skills", ""),
                "notes": details.get("top_projects", "")  # Using 'top_projects' to store extra context/notes
            })
            
        return jobs_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch job details: {e}")
