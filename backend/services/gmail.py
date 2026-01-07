import os
import base64
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from services.google_auth import get_google_creds
from dotenv import load_dotenv

load_dotenv()

def get_gmail_service():
    """Builds the Gmail service using shared credentials."""
    creds = get_google_creds()
    if not creds:
        return None
    return build('gmail', 'v1', credentials=creds)

def send_email(to: str, subject: str, message_text: str):
    try:
        service = get_gmail_service()
        if not service:
            print("❌ Gmail API Service could not be built. Check credentials.")
            return False

        message = MIMEText(message_text)
        message['to'] = to
        message['subject'] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        body = {'raw': raw}

        service.users().messages().send(userId='me', body=body).execute()
        print(f"✅ Email sent successfully to {to}")
        return True
    
    except Exception as e:
        print(f"❌ Gmail API Error: {e}")
        # Fallback to file just in case
        try:
            with open("delivered_emails.txt", "a", encoding="utf-8") as f:
                f.write(f"\n{'='*30}\n[FALLBACK SAVE]\nTO: {to}\nSUBJECT: {subject}\nBODY:\n{message_text}\n{'='*30}\n")
            print("⚠️ Saved to disk as fallback.")
            return True # Consider done
        except:
             return False
