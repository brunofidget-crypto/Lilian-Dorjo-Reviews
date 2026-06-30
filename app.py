#!/usr/bin/env python3
"""
app.py — Lilian Dorjo Client Experience Form
Every submission is saved instantly to Google Sheets (permanent) + emailed to Lilian.
"""

import base64, json, os, smtplib, datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import Flask, request, jsonify, send_from_directory, abort

# ─── Config ────────────────────────────────────────────────────────────────
BASE_DIR      = Path(__file__).parent
PORT          = int(os.environ.get("PORT", 8080))
LILIAN_EMAIL  = "Liliandrealtor25@gmail.com"
SHEET_ID      = os.environ.get("GOOGLE_SHEET_ID", "1Ut51gVmWf4b6pZ-1HyTQ857aLiY9aysLISca2hJVAhg")
GOOGLE_SA_B64 = os.environ.get("GOOGLE_SA_B64", "")   # base64-encoded service account JSON

SMTP_HOST = os.environ.get("EMAIL_HOST",     "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("EMAIL_PORT", 587))
SMTP_USER = os.environ.get("EMAIL_USER",     "")
SMTP_PASS = os.environ.get("EMAIL_PASSWORD", "")
FROM_NAME = "Lilian Dorjo"
FROM_ADDR = SMTP_USER

SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"

app      = Flask(__name__, static_folder=".", static_url_path="")
executor = ThreadPoolExecutor(max_workers=4)   # persistent thread pool


# ─── Google Sheets — init once at startup ───────────────────────────────────
_ws = None   # the worksheet object, reused for all writes

def _init_sheets():
    global _ws
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        SCOPES = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]

        if GOOGLE_SA_B64:
            decoded = base64.b64decode(GOOGLE_SA_B64).decode("utf-8")
            info    = json.loads(decoded)
            creds   = Credentials.from_service_account_info(info, scopes=SCOPES)
            print("[sheets] ✅ Service account loaded from env var", flush=True)
        else:
            sa_path = (
                Path(__file__).parent.parent.parent.parent.parent
                / "service_account.json"
                / "lilians-form-35954bdfeecd.json"
            )
            creds = Credentials.from_service_account_file(str(sa_path), scopes=SCOPES)
            print(f"[sheets] ✅ Service account loaded from file: {sa_path}", flush=True)

        client = gspread.authorize(creds)
        sh     = client.open_by_key(SHEET_ID)
        _ws    = sh.sheet1
        print(f"[sheets] ✅ Connected to sheet: {sh.title}", flush=True)
    except Exception as e:
        print(f"[sheets] ❌ Init failed: {e}", flush=True)
        _ws = None

# Run once at startup
_init_sheets()


def append_to_sheet(data: dict):
    """Append one submission row to the worksheet."""
    if _ws is None:
        print("[sheets] ❌ No worksheet — skipping write", flush=True)
        return
    try:
        stars  = data.get("stars", [])
        s      = (stars + [0]*6)[:6]
        avg    = round(sum(stars)/max(len(stars), 1), 2) if stars else 0
        ts_raw = data.get("submittedAt", "")
        try:
            dt = datetime.datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
            ts = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        except Exception:
            ts = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        _ws.append_row([
            ts,
            data.get("firstName", ""),
            data.get("lastName",  ""),
            data.get("language",  ""),
            data.get("location",  ""),
            s[0], s[1], s[2], s[3], s[4], s[5],
            avg,
            data.get("thoughts",    ""),
            data.get("fillSeconds", ""),
        ], value_input_option="USER_ENTERED")
        print(f"[sheets] ✅ Row saved — {data.get('firstName')} {data.get('lastName')}", flush=True)
    except Exception as e:
        print(f"[sheets] ❌ Write failed: {e}", flush=True)


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


@app.route("/health")
def health():
    return jsonify({
        "ok":        True,
        "sheets":    _ws is not None,
        "sheet_url": SHEET_URL,
    })


@app.route("/submit", methods=["POST"])
def submit():
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"ok": False, "error": "Invalid JSON"}), 400

    # Submit to thread pool (survives past response, unlike daemon threads)
    executor.submit(append_to_sheet, data)
    executor.submit(notify_lilian,   data)

    return jsonify({"ok": True})


# ─── Email ──────────────────────────────────────────────────────────────────
def send_email(to, subject, html):
    if not SMTP_USER or not SMTP_PASS:
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
        print(f"[email] ✅ Sent to {to}", flush=True)
    except Exception as e:
        print(f"[email] ❌ {e}", flush=True)


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
