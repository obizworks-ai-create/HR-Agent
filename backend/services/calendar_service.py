from datetime import datetime, timedelta
import pytz
import os
from googleapiclient.discovery import build
from services.google_auth import get_google_creds

def get_calendar_service():
    creds = get_google_creds()
    if not creds:
        return None
    return build('calendar', 'v3', credentials=creds)

def find_available_slot(duration_minutes=45):
    """
    Finds the next available slot in the primary calendar during work hours (9am-5pm).
    Scans the next 5 working days.
    """
    service = get_calendar_service()
    if not service:
        return None

    now = datetime.utcnow()
    # Start looking from tomorrow 9 AM to avoid immediate conflicts
    start_search = now + timedelta(days=1)
    
    # Simple heuristic: Look for slots in next 7 days
    for day_offset in range(7):
        current_day = start_search + timedelta(days=day_offset)
        
        # Skip weekends (5=Sat, 6=Sun)
        if current_day.weekday() >= 5:
            continue
            
        # Work hours: 9 AM to 5 PM (UTC assuming user is mostly global, or could fix to local)
        # For simplicity in this agent, using a fixed window. 
        # Ideally we'd user's timezone, but defaulting to 'Z' (UTC) for API consistency.
        
        work_start = current_day.replace(hour=9, minute=0, second=0, microsecond=0)
        work_end = current_day.replace(hour=17, minute=0, second=0, microsecond=0)
        
        # Check FreeBusy
        body = {
            "timeMin": work_start.isoformat() + 'Z',
            "timeMax": work_end.isoformat() + 'Z',
            "timeZone": 'UTC',
            "items": [{"id": "primary"}]
        }
        
        events_result = service.freebusy().query(body=body).execute()
        busy_slots = events_result['calendars']['primary']['busy']
        
        # Naive slot finding: iterate in chunks
        current_slot = work_start
        found = False
        
        while current_slot + timedelta(minutes=duration_minutes) <= work_end:
            slot_end = current_slot + timedelta(minutes=duration_minutes)
            
            # Check overlap
            is_busy = False
            for busy in busy_slots:
                b_start = datetime.fromisoformat(busy['start'].replace('Z', '+00:00')).replace(tzinfo=None)
                b_end = datetime.fromisoformat(busy['end'].replace('Z', '+00:00')).replace(tzinfo=None)
                
                # Check intersection
                if not (slot_end <= b_start or current_slot >= b_end):
                    is_busy = True
                    break
            
            if not is_busy:
                return current_slot
            
            # Move to next slot (e.g. start on hour/half-hour)
            current_slot += timedelta(minutes=30)
            
    return None

def schedule_interview(candidate_name, candidate_email, job_title, fixed_date=None, fixed_time=None):
    service = get_calendar_service()
    if not service:
        return "Failed to connect to Calendar"

    start_time = None
    end_time = None

    if fixed_date and fixed_time:
        # Manual Scheduling
        try:
            # Parse inputs (YYYY-MM-DD and HH:MM)
            dt_str = f"{fixed_date} {fixed_time}"
            # Naive parse, assume UTC or system local? 
            # The user wants "time in their calendar". 
            # We will interpret this as UTC for simplicity or standard ISO if frontend sends it.
            # Ideally frontend sends ISO, but task said "select time".
            # Let's assume input is "2024-01-01" and "14:00"
            
            dt_obj = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
            
            # Format as ISO 
            start_time = dt_obj.isoformat() + 'Z' # Treat as UTC or Z-time for now to avoid complexity
            end_time = (dt_obj + timedelta(minutes=45)).isoformat() + 'Z'
            
            slot = dt_obj # For display
        except ValueError:
            return "Invalid Date/Time format. Use YYYY-MM-DD and HH:MM"
    else:
        # Auto Scheduling
        slot = find_available_slot()
        if not slot:
            return "No available slots found in next 7 days"
            
        start_time = slot.isoformat() + 'Z'
        end_time = (slot + timedelta(minutes=45)).isoformat() + 'Z'
    
    attendees_list = []
    if candidate_email and "@" in candidate_email:
        attendees_list.append({'email': candidate_email})
    else:
        print(f"⚠️ Warning: Invalid or missing email for {candidate_name} ('{candidate_email}'). Scheduling without invite.")

    from urllib.parse import quote
    encoded_email = quote(candidate_email)
    encoded_job = quote(job_title)

    form_link = "https://forms.gle/qGQ5oURYtTowECz58"
    base_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    interview_link = f"{base_url}/interview?email={encoded_email}&job={encoded_job}"
    
    description = (
        f"Automated interview scheduling for {candidate_name}.\n"
        f"Contact Info: {candidate_email}\n\n"
        f"🎙️ VOICE INTERVIEW LINK: Please click here to start your AI Interview at the scheduled time:\n"
        f"{interview_link}\n\n"
        f"IMPORTANT: Please fill out this Pre-Screening Form before the interview:\n"
        f"{form_link}"
    )


    event = {
        'summary': f'Interview: {candidate_name} for {job_title}',
        'location': 'Online / Google Meet',
        'description': description,
        'start': {
            'dateTime': start_time,
            'timeZone': 'UTC',
        },
        'end': {
            'dateTime': end_time,
            'timeZone': 'UTC',
        },
        'attendees': attendees_list,
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 24 * 60},
                {'method': 'popup', 'minutes': 10},
            ],
        },
    }

    try:
        event = service.events().insert(calendarId='primary', body=event, sendUpdates='all').execute()
        return f"Scheduled for {slot.strftime('%Y-%m-%d %H:%M UTC')} (Link: {event.get('htmlLink')})"
    except Exception as e:
        return f"Error creating event: {str(e)}"
