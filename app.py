#!/usr/bin/env python3
"""
app.py — Lilian Dorjo Client Experience Form
Every submission is saved instantly to Google Sheets (permanent) + emailed to Lilian.
"""

import json, os, smtplib, datetime, threading
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import Flask, request, jsonify, send_from_directory, abort

# ─── Config ────────────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).parent
PORT         = int(os.environ.get("PORT", 8080))
LILIAN_EMAIL = "Liliandrealtor25@gmail.com"
SHEET_ID     = os.environ.get("GOOGLE_SHEET_ID", "1Ut51gVmWf4b6pZ-1HyTQ857aLiY9aysLISca2hJVAhg")
SA_JSON      = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")  # full JSON string on Railway

SMTP_HOST = os.environ.get("EMAIL_HOST",     "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("EMAIL_PORT", 587))
SMTP_USER = os.environ.get("EMAIL_USER",     "")
SMTP_PASS = os.environ.get("EMAIL_PASSWORD", "")
FROM_NAME = "Lilian Dorjo"
FROM_ADDR = SMTP_USER

app = Flask(__name__, static_folder=".", static_url_path="")

SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"

# ─── Google Sheets client ───────────────────────────────────────────────────
def _sheets_client():
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        SCOPES = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]

        if SA_JSON:
            # Railway: credentials stored as env var JSON string
            info = json.loads(SA_JSON)
            creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        else:
            # Local fallback: read the file
            sa_path = (
                Path(__file__).parent.parent.parent.parent.parent
                / "service_account.json"
                / "lilians-form-35954bdfeecd.json"
            )
            creds = Credentials.from_service_account_file(str(sa_path), scopes=SCOPES)

        return gspread.authorize(creds)
    except Exception as e:
        print(f"[sheets] Auth error: {e}")
        return None


def append_to_sheet(data: dict):
    """Append one row — runs in a background thread."""
    client = _sheets_client()
    if not client:
        print("[sheets] No client — skipping")
        return
    try:
        stars = data.get("stars", [])
        s     = (stars + [0]*6)[:6]
        avg   = round(sum(stars)/max(len(stars),1), 2) if stars else 0

        ts_raw = data.get("submittedAt", "")
        try:
            dt = datetime.datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
            ts = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        except Exception:
            ts = ts_raw

        row = [
            ts,
            data.get("firstName", ""),
            data.get("lastName",  ""),
            data.get("language",  ""),
            data.get("location",  ""),
            s[0], s[1], s[2], s[3], s[4], s[5],
            avg,
            data.get("thoughts",     ""),
            data.get("fillSeconds",  ""),
        ]
        sh = client.open_by_key(SHEET_ID)
        sh.sheet1.append_row(row, value_input_option="USER_ENTERED")
        print(f"[sheets] ✅ {data.get('firstName')} {data.get('lastName')}")
    except Exception as e:
        print(f"[sheets] ❌ {e}")


# ─── Routes ─────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "form.html")


@app.route("/Website/<path:filename>")
def serve_website_assets(filename):
    website_dir = BASE_DIR / "Website"
    fp = (website_dir / filename).resolve()
    try:
        fp.relative_to(website_dir.resolve())
    except ValueError:
        abort(403)
    if fp.is_file():
        return send_from_directory(website_dir, filename)
    abort(404)


@app.route("/submit", methods=["POST"])
def submit():
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"ok": False, "error": "Invalid JSON"}), 400

    # Save to Google Sheets (background — non-blocking)
    threading.Thread(target=append_to_sheet, args=(data,), daemon=True).start()
    # Email Lilian (background — non-blocking)
    threading.Thread(target=notify_lilian,   args=(data,), daemon=True).start()

    return jsonify({"ok": True})


# ─── Email ──────────────────────────────────────────────────────────────────
def send_email(to, subject, html):
    if not SMTP_USER or not SMTP_PASS:
        print(f"[email] SMTP not configured")
        return
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"{FROM_NAME} <{FROM_ADDR}>"
    msg["To"]      = to
    msg.attach(MIMEText(html, "html"))
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.ehlo(); s.starttls()
            s.login(SMTP_USER, SMTP_PASS)
            s.sendmail(FROM_ADDR, [to], msg.as_string())
        print(f"[email] Sent to {to}")
    except Exception as e:
        print(f"[email] ERROR: {e}")


def notify_lilian(data: dict):
    first     = data.get("firstName", "Someone")
    last      = data.get("lastName",  "")
    location  = data.get("location",  "Unknown")
    stars     = data.get("stars", [])
    avg       = round(sum(stars)/max(len(stars),1), 1) if stars else 0
    stars_str = "★" * round(avg) + "☆" * (5 - round(avg))
    submitted = data.get("submittedAt","")[:16].replace("T"," ")
    thoughts  = data.get("thoughts", "")

    thought_html = (
        f'<div style="border-left:3px solid #c9a84c;padding:12px 18px;'
        f'background:#fdfaf4;margin-bottom:20px;">'
        f'<p style="margin:0;font-style:italic;color:#333;font-size:14px;">'
        f'&ldquo;{thoughts}&rdquo;</p></div>'
    ) if thoughts else ""

    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"/></head>
<body style="font-family:Georgia,serif;background:#f5f3ef;margin:0;padding:32px 20px;">
<div style="max-width:540px;margin:0 auto;background:#fff;border-top:3px solid #c9a84c;padding:36px 44px;">
  <p style="font-size:11px;letter-spacing:3px;text-transform:uppercase;color:#c9a84c;margin:0 0 8px;">New Feedback Submission</p>
  <h2 style="font-size:22px;color:#0d1b2a;font-weight:600;margin:0 0 24px;">Hi Lilian,</h2>
  <p style="font-size:15px;color:#333;line-height:1.75;margin:0 0 20px;">
    <strong>{first} {last}</strong> just completed your client feedback form.
  </p>
  <table style="border-collapse:collapse;width:100%;margin-bottom:24px;">
    <tr><td style="padding:10px 14px;background:#f5f3ef;font-size:13px;color:#666;">Location</td>
        <td style="padding:10px 14px;background:#f5f3ef;font-size:14px;color:#0d1b2a;font-weight:600;">{location}</td></tr>
    <tr><td style="padding:10px 14px;font-size:13px;color:#666;">Avg. Score</td>
        <td style="padding:10px 14px;font-size:16px;color:#c9a84c;">{stars_str} ({avg}/5.0)</td></tr>
    <tr><td style="padding:10px 14px;background:#f5f3ef;font-size:13px;color:#666;">Submitted</td>
        <td style="padding:10px 14px;background:#f5f3ef;font-size:13px;color:#0d1b2a;">{submitted} UTC</td></tr>
  </table>
  {thought_html}
  <p style="margin:20px 0 0;">
    <a href="{SHEET_URL}" style="color:#c9a84c;font-size:13px;font-weight:bold;">📊 View all responses in Google Sheets →</a>
  </p>
</div>
</body></html>"""

    send_email(LILIAN_EMAIL, f"New Review — {first} {last}", html)


# ─── Entry point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
