#!/usr/bin/env python3
"""
setup_sheets.py — One-time local setup for Lilian's Google Sheets integration
─────────────────────────────────────────────────────────────────────────────
Run this ONCE on your local machine. It will:
  1. Open your browser to authorise with Google (one click)
  2. Create the "Lilian Dorjo – Client Reviews" Google Sheet
  3. Write the correct column headers
  4. Print the two env-var values you paste into Railway

Usage:
    cd "Other Projects/Website Assets/Lilian Real estate/deploy"
    pip install gspread google-auth-oauthlib
    python3 setup_sheets.py
"""

import json, sys
from pathlib import Path

# ── Try importing required libraries ──────────────────────────────────────
try:
    import gspread
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
except ImportError:
    print("Installing required packages …")
    import subprocess
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "-q",
        "gspread", "google-auth-oauthlib"
    ])
    import gspread
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

CREDS_FILE  = Path(__file__).parent.parent.parent.parent.parent / "credentials.json"  # workspace root
TOKEN_FILE  = Path(__file__).parent / "token.json"
SHEET_ID_FILE = Path(__file__).parent / ".sheet_id"

HEADERS = [
    "Submitted At",
    "First Name",
    "Last Name",
    "Language",
    "Location",
    "⭐ Overall Experience",
    "⭐ Response Time & Availability",
    "⭐ Clarity Throughout",
    "⭐ Smoothness Start→Finish",
    "⭐ Level of Trust",
    "⭐ Satisfaction with Outcome",
    "Average Stars",
    "Written Thoughts",
    "Fill Time (seconds)",
]


def authenticate():
    """OAuth2 flow – opens browser once, saves token.json."""
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing existing token …")
            creds.refresh(Request())
        else:
            print("\n🌐  A browser window will open – sign in with your Google account.")
            if not CREDS_FILE.exists():
                print(f"\n❌  credentials.json not found at:\n    {CREDS_FILE}")
                print("Place the credentials.json in the AntiGravity Workspace root folder.")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)

        TOKEN_FILE.write_text(creds.to_json())
        print("✅  Token saved to token.json")

    return creds


def create_sheet(client):
    """Create the Lilian reviews spreadsheet and return it."""
    title = "Lilian Dorjo – Client Reviews"

    # Check if sheet already exists
    try:
        existing = client.open(title)
        print(f"✅  Sheet already exists: {existing.url}")
        return existing
    except gspread.exceptions.SpreadsheetNotFound:
        pass

    sh = client.create(title)
    sh.share(None, perm_type="anyone", role="reader")   # anyone with link can view
    print(f"✅  Sheet created: {sh.url}")
    return sh


def setup_headers(sheet):
    """Write header row with formatting."""
    ws = sheet.sheet1
    ws.update_title("Responses")

    # Write headers
    ws.append_row(HEADERS, value_input_option="USER_ENTERED")

    # Bold the header row (best-effort – requires Sheets v4)
    try:
        sheet.batch_update({
            "requests": [{
                "repeatCell": {
                    "range": {
                        "sheetId": ws.id,
                        "startRowIndex": 0,
                        "endRowIndex": 1,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "textFormat": {"bold": True},
                            "backgroundColor": {"red": 0.11, "green": 0.11, "blue": 0.16},
                        }
                    },
                    "fields": "userEnteredFormat(textFormat,backgroundColor)",
                }
            }]
        })
    except Exception:
        pass  # formatting is optional

    print(f"✅  Headers written to sheet")


def main():
    print("=" * 60)
    print("  Lilian Dorjo – Google Sheets Setup")
    print("=" * 60)

    # 1. Authenticate
    creds = authenticate()

    # 2. Connect to Sheets
    client = gspread.authorize(creds)

    # 3. Create / open sheet
    sh = create_sheet(client)

    # Check if headers already written
    ws = sh.sheet1
    existing_headers = ws.row_values(1)
    if not existing_headers:
        setup_headers(sh)
    else:
        print("✅  Headers already present – skipping")

    # 4. Save sheet ID
    SHEET_ID_FILE.write_text(sh.id)

    # 5. Print Railway env vars
    token_data = json.loads(TOKEN_FILE.read_text())
    token_json_str = json.dumps(token_data)

    print("\n" + "=" * 60)
    print("  ✅  Setup complete!")
    print("=" * 60)
    print(f"\n📊  Sheet URL:\n    {sh.url}\n")
    print("🚂  Add these TWO environment variables to Railway:\n")
    print(f"  GOOGLE_SHEET_ID = {sh.id}\n")
    print(f"  GOOGLE_TOKEN_JSON = {token_json_str}\n")
    print("=" * 60)
    print("  Copy the values above → Railway → Variables → Add")
    print("=" * 60)


if __name__ == "__main__":
    main()
