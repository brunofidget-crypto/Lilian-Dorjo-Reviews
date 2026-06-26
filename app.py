#!/usr/bin/env python3
"""
app.py — Lilian Dorjo Client Experience Form
Cloud-ready Flask server for deployment on Render.com
"""

import json
import os
import smtplib
import datetime
import threading
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import Flask, request, jsonify, send_from_directory, abort

# ─── Config ────────────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).parent
DATA_FILE    = BASE_DIR / "submissions.json"
PORT         = int(os.environ.get("PORT", 8080))
LILIAN_EMAIL = "Liliandrealtor25@gmail.com"

SMTP_HOST = os.environ.get("EMAIL_HOST",     "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("EMAIL_PORT", 587))
SMTP_USER = os.environ.get("EMAIL_USER",     "")
SMTP_PASS = os.environ.get("EMAIL_PASSWORD", "")
FROM_NAME = "Lilian Dorjo"
FROM_ADDR = SMTP_USER

app = Flask(__name__, static_folder=".", static_url_path="")


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

    save_submission(data)

    # Notify Lilian in background
    t = threading.Thread(target=notify_lilian, args=(data,), daemon=True)
    t.start()

    return jsonify({"ok": True})


# ─── Storage ────────────────────────────────────────────────────────────────
def load_submissions():
    if not DATA_FILE.exists():
        return []
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_submission(data: dict):
    subs = load_submissions()
    subs.append(data)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(subs, f, indent=2, ensure_ascii=False)


# ─── Email ──────────────────────────────────────────────────────────────────
def send_email(to: str, subject: str, html: str):
    if not SMTP_USER or not SMTP_PASS:
        print(f"[email] SMTP not configured — skipping email to {to}")
        return
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"{FROM_NAME} <{FROM_ADDR}>"
    msg["To"]      = to
    msg.attach(MIMEText(html, "html"))
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(FROM_ADDR, [to], msg.as_string())
        print(f"[email] Sent to {to}")
    except Exception as e:
        print(f"[email] ERROR: {e}")


def notify_lilian(data: dict):
    first    = data.get("firstName", "Someone")
    last     = data.get("lastName",  "")
    location = data.get("location",  "Unknown")
    stars    = data.get("stars", [])
    avg      = round(sum(stars) / max(len(stars), 1), 1) if stars else 0
    stars_str = "★" * round(avg) + "☆" * (5 - round(avg))
    submitted = data.get("submittedAt", "")[:16].replace("T", " ")
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
    <tr>
      <td style="padding:10px 14px;background:#f5f3ef;font-size:13px;color:#666;">Location</td>
      <td style="padding:10px 14px;background:#f5f3ef;font-size:14px;color:#0d1b2a;font-weight:600;">{location}</td>
    </tr>
    <tr>
      <td style="padding:10px 14px;font-size:13px;color:#666;">Avg. Score</td>
      <td style="padding:10px 14px;font-size:16px;color:#c9a84c;">{stars_str} ({avg}/5.0)</td>
    </tr>
    <tr>
      <td style="padding:10px 14px;background:#f5f3ef;font-size:13px;color:#666;">Submitted</td>
      <td style="padding:10px 14px;background:#f5f3ef;font-size:13px;color:#0d1b2a;">{submitted} UTC</td>
    </tr>
  </table>
  {thought_html}
  <p style="font-size:13px;color:#999;margin:0;">You'll receive your weekly analytics summary every Monday.</p>
</div>
</body></html>"""

    send_email(LILIAN_EMAIL, f"New Review — {first} {last}", html)


# ─── Entry point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
