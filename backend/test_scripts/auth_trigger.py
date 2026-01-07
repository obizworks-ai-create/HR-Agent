from services.google_auth import get_google_creds

print("🚀 Attempting to trigger Google Login...")
creds = get_google_creds()

if creds and creds.valid:
    print("\n✅ Authentication Successful!")
    print("Helper: You are now logged in. The token.json file has been created.")
else:
    print("\n❌ Authentication failed or was cancelled.")
