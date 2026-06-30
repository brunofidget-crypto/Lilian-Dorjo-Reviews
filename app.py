#!/usr/bin/env python3
"""
app.py — Lilian Dorjo Client Experience Form
Storage: PostgreSQL on Railway (persistent forever) + local SQLite fallback
Access:  /dashboard  — view all responses in a clean table
         /export.csv — download all responses as CSV
"""

import csv
import io
import json
import os
import smtplib
import datetime
import threading
import secrets
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import Flask, request, jsonify, send_from_directory, abort, Response, render_template_string

# ─── Config ────────────────────────────────────────────────────────────────
BASE_DIR      = Path(__file__).parent
PORT          = int(os.environ.get("PORT", 8080))
LILIAN_EMAIL  = "Liliandrealtor25@gmail.com"
DATABASE_URL  = os.environ.get("DATABASE_URL", "")   # auto-set by Railway PostgreSQL plugin
ADMIN_KEY     = os.environ.get("ADMIN_KEY", "lilian2025")  # password to view dashboard/CSV

SMTP_HOST = os.environ.get("EMAIL_HOST",     "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("EMAIL_PORT", 587))
SMTP_USER = os.environ.get("EMAIL_USER",     "")
SMTP_PASS = os.environ.get("EMAIL_PASSWORD", "")
FROM_NAME = "Lilian Dorjo"
FROM_ADDR = SMTP_USER

app = Flask(__name__, static_folder=".", static_url_path="")


# ─── Database setup ─────────────────────────────────────────────────────────
def get_db():
    """Return a database connection — PostgreSQL on Railway, SQLite locally."""
    if DATABASE_URL:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        return conn, "pg"
    else:
        import sqlite3
        conn = sqlite3.connect(BASE_DIR / "submissions.db")
        conn.row_factory = sqlite3.Row
        return conn, "sqlite"


def init_db():
    """Create the submissions table if it doesn't exist."""
    conn, kind = get_db()
    try:
        cur = conn.cursor()
        if kind == "pg":
            cur.execute("""
                CREATE TABLE IF NOT EXISTS submissions (
                    id           SERIAL PRIMARY KEY,
                    submitted_at TIMESTAMPTZ DEFAULT NOW(),
                    first_name   TEXT,
                    last_name    TEXT,
                    language     TEXT,
                    location     TEXT,
                    star_overall     INT,
                    star_response    INT,
                    star_clarity     INT,
                    star_smoothness  INT,
                    star_trust       INT,
                    star_satisfaction INT,
                    avg_stars    NUMERIC(3,2),
                    thoughts     TEXT,
                    fill_seconds INT
                )
            """)
        else:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS submissions (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    submitted_at TEXT DEFAULT (datetime('now')),
                    first_name   TEXT,
                    last_name    TEXT,
                    language     TEXT,
                    location     TEXT,
                    star_overall     INTEGER,
                    star_response    INTEGER,
                    star_clarity     INTEGER,
                    star_smoothness  INTEGER,
                    star_trust       INTEGER,
                    star_satisfaction INTEGER,
                    avg_stars    REAL,
                    thoughts     TEXT,
                    fill_seconds INTEGER
                )
            """)
        conn.commit()
        print("[db] ✅ Table ready")
    finally:
        conn.close()


def insert_submission(data: dict):
    """Insert one submission row."""
    stars = data.get("stars", [])
    s     = (stars + [0]*6)[:6]
    avg   = round(sum(stars) / max(len(stars), 1), 2) if stars else 0

    # Parse timestamp
    ts_raw = data.get("submittedAt", "")
    try:
        dt = datetime.datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
        ts = dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        ts = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    conn, kind = get_db()
    try:
        cur = conn.cursor()
        if kind == "pg":
            cur.execute("""
                INSERT INTO submissions
                (submitted_at, first_name, last_name, language, location,
                 star_overall, star_response, star_clarity, star_smoothness,
                 star_trust, star_satisfaction, avg_stars, thoughts, fill_seconds)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (ts, data.get("firstName",""), data.get("lastName",""),
                  data.get("language",""), data.get("location",""),
                  s[0],s[1],s[2],s[3],s[4],s[5], avg,
                  data.get("thoughts",""), data.get("fillSeconds",0)))
        else:
            cur.execute("""
                INSERT INTO submissions
                (submitted_at, first_name, last_name, language, location,
                 star_overall, star_response, star_clarity, star_smoothness,
                 star_trust, star_satisfaction, avg_stars, thoughts, fill_seconds)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (ts, data.get("firstName",""), data.get("lastName",""),
                  data.get("language",""), data.get("location",""),
                  s[0],s[1],s[2],s[3],s[4],s[5], avg,
                  data.get("thoughts",""), data.get("fillSeconds",0)))
        conn.commit()
        print(f"[db] ✅ Saved: {data.get('firstName')} {data.get('lastName')}")
    finally:
        conn.close()


def fetch_all():
    """Return all submissions newest-first as a list of dicts."""
    conn, kind = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM submissions ORDER BY submitted_at DESC")
        rows = cur.fetchall()
        if kind == "pg":
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in rows]
        else:
            return [dict(r) for r in rows]
    finally:
        conn.close()


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

    # Save to DB (synchronous — must succeed before returning ok)
    try:
        insert_submission(data)
    except Exception as e:
        print(f"[db] ❌ Insert failed: {e}")
        # Still return ok to user — save to JSON fallback
        _save_json_backup(data)

    # Email Lilian in background
    threading.Thread(target=notify_lilian, args=(data,), daemon=True).start()

    return jsonify({"ok": True})


@app.route("/dashboard")
def dashboard():
    """Clean table of all submissions — password protected."""
    key = request.args.get("key", "")
    if key != ADMIN_KEY:
        return Response(
            '<html><body style="font-family:sans-serif;padding:40px;">'
            '<h2>🔒 Access Restricted</h2>'
            '<p>Add <code>?key=YOUR_PASSWORD</code> to the URL</p>'
            '</body></html>',
            status=401, mimetype="text/html"
        )

    rows = fetch_all()
    total = len(rows)
    avg_all = round(sum(float(r.get("avg_stars") or 0) for r in rows) / max(total, 1), 2)

    rows_html = ""
    for r in rows:
        stars_display = "⭐" * round(float(r.get("avg_stars") or 0))
        thoughts = (r.get("thoughts") or "")[:120]
        thoughts_cell = f'<em style="color:#555">{thoughts}</em>' if thoughts else '<span style="color:#aaa">—</span>'
        rows_html += f"""
        <tr>
          <td>{r.get('submitted_at','')}</td>
          <td><strong>{r.get('first_name','')} {r.get('last_name','')}</strong></td>
          <td>{r.get('location','')}</td>
          <td>{r.get('language','').upper()}</td>
          <td>{r.get('star_overall','')} / {r.get('star_response','')} / {r.get('star_clarity','')} / {r.get('star_smoothness','')} / {r.get('star_trust','')} / {r.get('star_satisfaction','')}</td>
          <td style="color:#c9a84c;font-size:18px;">{stars_display} <small style="color:#666">({r.get('avg_stars','')})</small></td>
          <td>{thoughts_cell}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Lilian Dorjo — Client Reviews</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'Georgia',serif;background:#f5f3ef;color:#0d1b2a;padding:32px 20px}}
  .wrap{{max-width:1200px;margin:0 auto}}
  h1{{font-size:28px;color:#0d1b2a;margin-bottom:4px}}
  .subtitle{{color:#888;font-size:14px;margin-bottom:32px}}
  .stats{{display:flex;gap:24px;margin-bottom:32px;flex-wrap:wrap}}
  .stat{{background:#fff;border:1px solid #e0ddd8;padding:20px 28px;border-radius:10px;min-width:140px}}
  .stat-val{{font-size:32px;font-weight:700;color:#c9a84c}}
  .stat-lbl{{font-size:12px;color:#888;letter-spacing:.05em;text-transform:uppercase;margin-top:4px}}
  .actions{{margin-bottom:20px}}
  .btn{{display:inline-block;padding:10px 20px;background:#0d1b2a;color:#fff;text-decoration:none;border-radius:6px;font-size:13px;margin-right:8px}}
  .btn:hover{{background:#c9a84c}}
  table{{width:100%;border-collapse:collapse;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.06)}}
  th{{background:#0d1b2a;color:#c9a84c;padding:12px 14px;font-size:11px;letter-spacing:.08em;text-transform:uppercase;text-align:left}}
  td{{padding:12px 14px;font-size:13px;border-bottom:1px solid #f0ede8;vertical-align:top}}
  tr:last-child td{{border-bottom:none}}
  tr:hover td{{background:#fdfaf4}}
</style>
</head>
<body>
<div class="wrap">
  <h1>Lilian Dorjo — Client Reviews</h1>
  <p class="subtitle">All submissions • newest first</p>
  <div class="stats">
    <div class="stat"><div class="stat-val">{total}</div><div class="stat-lbl">Total Responses</div></div>
    <div class="stat"><div class="stat-val">{avg_all}</div><div class="stat-lbl">Avg. Rating / 5</div></div>
  </div>
  <div class="actions">
    <a class="btn" href="/export.csv?key={ADMIN_KEY}">⬇ Download CSV</a>
  </div>
  <table>
    <thead>
      <tr>
        <th>Date & Time</th><th>Name</th><th>Location</th><th>Lang</th>
        <th>Stars (6 categories)</th><th>Avg</th><th>Written Thoughts</th>
      </tr>
    </thead>
    <tbody>
      {rows_html if rows_html else '<tr><td colspan="7" style="text-align:center;padding:40px;color:#aaa;">No submissions yet</td></tr>'}
    </tbody>
  </table>
</div>
</body></html>"""
    return Response(html, mimetype="text/html")


@app.route("/export.csv")
def export_csv():
    """Download all submissions as a CSV file — password protected."""
    key = request.args.get("key", "")
    if key != ADMIN_KEY:
        abort(401)

    rows = fetch_all()
    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow([
        "Submitted At", "First Name", "Last Name", "Language", "Location",
        "Overall Experience", "Response Time & Availability",
        "Clarity Throughout", "Smoothness Start→Finish",
        "Level of Trust", "Satisfaction with Outcome",
        "Average Stars", "Written Thoughts", "Fill Time (seconds)"
    ])

    for r in rows:
        writer.writerow([
            r.get("submitted_at",""),
            r.get("first_name",""),
            r.get("last_name",""),
            r.get("language",""),
            r.get("location",""),
            r.get("star_overall",""),
            r.get("star_response",""),
            r.get("star_clarity",""),
            r.get("star_smoothness",""),
            r.get("star_trust",""),
            r.get("star_satisfaction",""),
            r.get("avg_stars",""),
            r.get("thoughts",""),
            r.get("fill_seconds",""),
        ])

    csv_data = output.getvalue()
    filename = f"lilian_reviews_{datetime.date.today()}.csv"
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ─── JSON fallback backup ───────────────────────────────────────────────────
def _save_json_backup(data: dict):
    backup = BASE_DIR / "submissions_backup.json"
    try:
        existing = json.loads(backup.read_text()) if backup.exists() else []
        existing.append(data)
        backup.write_text(json.dumps(existing, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"[backup] ❌ {e}")


# ─── Email notification ─────────────────────────────────────────────────────
def send_email(to: str, subject: str, html: str):
    if not SMTP_USER or not SMTP_PASS:
        print(f"[email] SMTP not configured — skipping")
        return
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"{FROM_NAME} <{FROM_ADDR}>"
    msg["To"]      = to
    msg.attach(MIMEText(html, "html"))
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo(); server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(FROM_ADDR, [to], msg.as_string())
        print(f"[email] Sent to {to}")
    except Exception as e:
        print(f"[email] ERROR: {e}")


def notify_lilian(data: dict):
    first     = data.get("firstName", "Someone")
    last      = data.get("lastName",  "")
    location  = data.get("location",  "Unknown")
    stars     = data.get("stars", [])
    avg       = round(sum(stars) / max(len(stars), 1), 1) if stars else 0
    stars_str = "★" * round(avg) + "☆" * (5 - round(avg))
    submitted = data.get("submittedAt", "")[:16].replace("T", " ")
    thoughts  = data.get("thoughts", "")

    dashboard_link = (
        f'<p style="margin:16px 0 0;font-size:13px;">'
        f'<a href="https://lilian-dorjo-reviews-production.up.railway.app/dashboard?key={ADMIN_KEY}" '
        f'style="color:#c9a84c;font-weight:bold;">📊 View all responses →</a></p>'
    )

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
  {dashboard_link}
</div>
</body></html>"""
    send_email(LILIAN_EMAIL, f"New Review — {first} {last}", html)


# ─── Entry point ────────────────────────────────────────────────────────────
with app.app_context():
    try:
        init_db()
    except Exception as e:
        print(f"[db] ⚠️ init_db failed: {e} — will retry on first request")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
