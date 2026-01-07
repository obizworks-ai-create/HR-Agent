"""
Simple script to trigger Google OAuth authentication.
This will open a browser and prompt you to sign in with obizworks-ai@pctsc.com

Run this from the backend directory:
    python test_auth.py
"""

from services.google_auth import get_google_creds
from services.gmail import get_gmail_service
from services.calendar_service import get_calendar_service

print("=" * 60)
print("  Gmail Account Authentication Test")
print("  New Account: obizworks-ai@pctsc.com")
print("=" * 60)
print()
print("This script will:")
print("1. Open a browser window for Google OAuth")
print("2. Ask you to sign in to Google")
print("3. IMPORTANT: Sign in with obizworks-ai@pctsc.com")
print("4. Grant Gmail and Calendar permissions")
print("5. Create token.json with your credentials")
print()
input("Press ENTER to continue...")
print()

print("🔑 Authenticating...")
creds = get_google_creds()

if creds:
    print("✅ Authentication successful!")
    print()
    
    # Test Gmail service
    print("📧 Testing Gmail service...")
    gmail_service = get_gmail_service()
    if gmail_service:
        print("✅ Gmail service is working!")
    else:
        print("❌ Gmail service failed")
    
    # Test Calendar service
    print("📅 Testing Calendar service...")
    calendar_service = get_calendar_service()
    if calendar_service:
        print("✅ Calendar service is working!")
    else:
        print("❌ Calendar service failed")
    
    print()
    print("=" * 60)
    print("  Authentication Complete!")
    print("  You can now restart your backend and use the app.")
    print("=" * 60)
else:
    print("❌ Authentication failed!")
    print("Please check your credentials.json file and try again.")
