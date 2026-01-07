@router.get("/candidates/imported")
def get_imported_candidates(job_title: str):
    """
    Fetch RAW imported candidates from source sheet (not analyzed).
    This shows the candidates that were imported from Google Drive but haven't been evaluated yet.
    """
    from services.sheets import read_sheet
    
    # Read from the source sheet for this job
    source_sheet = f"{job_title}"
    
    try:
        rows = read_sheet(f"{source_sheet}!A:D")  # Name, Email, Phone, Resume Link
        
        if not rows or len(rows) < 2:  # Need at least header + 1 row
            return []
        
        headers = rows[0]
        data = []
        for r in rows[1:]:
            if len(r) < len(headers):
                r = r + [""] * (len(headers) - len(r))
            item = {h: val for h, val in zip(headers, r)}
            data.append(item)
        
        return data
    except Exception as e:
        print(f"Error fetching imported candidates: {e}")
        return []
