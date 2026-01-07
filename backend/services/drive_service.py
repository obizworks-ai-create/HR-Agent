import os
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from services.sheets import get_credentials

# Add Drive scope to the existing scopes logic in your head, 
# but since get_credentials in sheets.py is hardcoded with SCOPES, 
# we might need to update sheets.py or handle it here.
# ideally we refactor sheets.py to allow passing scopes, but for now 
# let's just create a local helper or modify sheets.py.
# Actually, I'll assume I can modify sheets.py to export SCOPES or allow overriding.
# For now, I'll copy the credential loading logic but with Drive scope.

from google.oauth2.service_account import Credentials
import json

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def get_drive_service():
    creds_path = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
    if not creds_path:
        # Fallback to API Key if Service Account not set (though highly recommended)
        # But for accessing private folders, Service Account is needed.
        # If the user specifically wants to use API Key, we'd build with developerKey.
        # build('drive', 'v3', developerKey=api_key)
        # However, listing folder usually requires OAuth for non-public.
        pass

    creds = None
    if os.path.exists(creds_path):
        creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    else:
        info = json.loads(creds_path)
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    
    return build('drive', 'v3', credentials=creds)

def list_files_in_folder(folder_id: str, min_date: str = None, max_date: str = None):
    """
    Lists files in the specified drive folder (all pages).
    Args:
        folder_id: ID of the folder to list.
        min_date: Optional ISO date string (YYYY-MM-DD) to filter files created on or after this date.
        max_date: Optional ISO date string (YYYY-MM-DD) to filter files created on or before this date.
    """
    service = get_drive_service()
    all_files = []
    page_token = None
    
    query = f"'{folder_id}' in parents and mimeType != 'application/vnd.google-apps.folder' and trashed=false"
    
    if min_date:
        # RFC 3339 format required by Drive API: YYYY-MM-DDTHH:MM:SS
        # Filter files created on or after min_date
        query += f" and modifiedTime >= '{min_date}T00:00:00'"
        
    if max_date:
        # Filter files created on or before max_date (end of day)
        query += f" and modifiedTime <= '{max_date}T23:59:59'"
        
    print(f"DEBUG: Drive Query -> {query}")

    while True:
        results = service.files().list(
            q=query,
            fields="nextPageToken, files(id, name, mimeType, createdTime, modifiedTime, webViewLink)",
            pageSize=100, 
            pageToken=page_token
        ).execute()
        
        all_files.extend(results.get('files', []))
        page_token = results.get('nextPageToken')
        if not page_token:
            break
            
    return all_files

def list_folders(parent_id: str):
    """Lists subfolders within a parent folder (all pages)."""
    service = get_drive_service()
    all_folders = []
    page_token = None
    
    while True:
        results = service.files().list(
            q=f"'{parent_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed=false",
            fields="nextPageToken, files(id, name)",
            pageSize=100,
            pageToken=page_token
        ).execute()
        
        all_folders.extend(results.get('files', []))
        page_token = results.get('nextPageToken')
        if not page_token:
            break
            
    return all_folders

def list_files_recursive(folder_id: str, min_date: str = None, max_date: str = None):
    """
    Recursively lists ALL files in a folder and its subfolders.
    Returns a flat list of file objects.
    """
    all_files = []
    
    # 1. Get files in current folder
    current_files = list_files_in_folder(folder_id, min_date, max_date)
    all_files.extend(current_files)
    
    # 2. Get subfolders (folders are NOT date filtered, we always traverse them to find files)
    subfolders = list_folders(folder_id)
    
    # 3. Recurse
    for folder in subfolders:
        # print(f"  ↪️ Entering subfolder: {folder['name']}")
        sub_files = list_files_recursive(folder['id'], min_date, max_date)
        all_files.extend(sub_files)
        
    return all_files

def download_file(file_id: str):
    """
    Downloads a file's content.
    Automatically handles Google Docs by exporting them as PDF.
    """
    service = get_drive_service()
    
    # Check mimeType first
    file_meta = service.files().get(fileId=file_id, fields="mimeType, name").execute()
    mime_type = file_meta.get('mimeType', '')
    
    if mime_type.startswith('application/vnd.google-apps.'):
        # It's a Google Doc/Sheet/Slide -> Export as DOCX (MS Word)
        print(f"  📄 Converting Google Doc '{file_meta.get('name')}' to DOCX...")
        request = service.files().export_media(
            fileId=file_id,
            mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
    else:
        # Binary file -> Download directly
        request = service.files().get_media(fileId=file_id)
        
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    return fh.getvalue()
