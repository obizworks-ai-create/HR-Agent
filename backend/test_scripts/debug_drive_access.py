import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
SERVICE_ACCOUNT_FILE = 'service_account.json'
FOLDER_ID = os.getenv('GOOGLE_DRIVE_FOLDER_ID')

def debug_drive():
    print("Authenticate...")
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        service = build('drive', 'v3', credentials=creds)
    except Exception as e:
        print(f"❌ Auth Failed: {e}")
        return

    print(f"\nTarget Folder ID from .env: {FOLDER_ID}")
    
    # 1. Check if we can see the Target Folder itself
    try:
        folder = service.files().get(fileId=FOLDER_ID, fields="id, name, mimeType").execute()
        print(f"✅ FOUND Target Folder: {folder['name']} (ID: {folder['id']})")
    except Exception as e:
        print(f"❌ CANNOT FIND Target Folder. Reason: {e}")
        print("   -> Tip: Did you share the folder with the Service Account email?")

    # 2. List ANYTHING we can see (to verify we have access to something)
    print("\nListing up to 10 files visible to this Service Account:")
    try:
        results = service.files().list(
            pageSize=10, fields="files(id, name, mimeType, parents)"
        ).execute()
        files = results.get('files', [])

        if not files:
            print("⚠️ No files found at all. The Service Account sees an empty Drive.")
        else:
            for f in files:
                print(f"   - {f['name']} ({f['mimeType']}) [IDs: {f['id']}] Parents: {f.get('parents', [])}")
                
    except Exception as e:
        print(f"❌ List Failed: {e}")

if __name__ == '__main__':
    debug_drive()
