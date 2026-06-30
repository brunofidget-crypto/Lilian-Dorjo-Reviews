/**
 * Lilian Dorjo – Client Reviews Webhook
 * ──────────────────────────────────────
 * Instructions (do this once):
 *  1. Open a new Google Sheet at sheets.google.com
 *  2. Click Extensions → Apps Script
 *  3. Delete all the default code
 *  4. Paste ALL of this code
 *  5. Click Save (floppy disk icon)
 *  6. Click Deploy → New deployment
 *  7. Click the gear icon next to "Type" → select Web app
 *  8. Description: "Lilian Reviews Webhook"
 *  9. Execute as: Me
 * 10. Who has access: Anyone
 * 11. Click Deploy → Authorize access → sign in → Allow
 * 12. Copy the Web app URL — paste it into Railway as APPS_SCRIPT_URL
 */

const SHEET_NAME = "Responses";

// ── Headers (must match app.py column order) ──────────────────────────────
const HEADERS = [
  "Submitted At (ET)",
  "First Name",
  "Last Name",
  "Language",
  "Location",
  "⭐ Overall Experience",
  "⭐ Response Time & Availability",
  "⭐ Clarity Throughout Process",
  "⭐ Smoothness Start → Finish",
  "⭐ Level of Trust",
  "⭐ Satisfaction with Outcome",
  "Average Stars",
  "Written Thoughts",
  "Fill Time (seconds)"
];


// ── Entry point for POST requests from Railway ────────────────────────────
function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);
    appendRow(data);
    return ContentService
      .createTextOutput(JSON.stringify({ ok: true }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({ ok: false, error: err.message }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}


// ── Write one row to the sheet ────────────────────────────────────────────
function appendRow(data) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let ws = ss.getSheetByName(SHEET_NAME);

  // Auto-create sheet + headers on first use
  if (!ws) {
    ws = ss.insertSheet(SHEET_NAME);
    ws.appendRow(HEADERS);

    // Bold + colour the header row
    const headerRange = ws.getRange(1, 1, 1, HEADERS.length);
    headerRange.setFontWeight("bold")
               .setBackground("#0d1b2a")
               .setFontColor("#c9a84c");
    ws.setFrozenRows(1);
  }

  // Stars array – pad to 6 slots
  const stars = Array.isArray(data.stars) ? data.stars : [];
  const s     = (stars.concat([0, 0, 0, 0, 0, 0])).slice(0, 6);
  const avg   = stars.length > 0
    ? parseFloat((stars.reduce((a, b) => a + b, 0) / stars.length).toFixed(2))
    : 0;

  // Convert UTC timestamp → Eastern Time
  let ts = data.submittedAt || new Date().toISOString();
  try {
    ts = Utilities.formatDate(
      new Date(ts),
      "America/New_York",
      "yyyy-MM-dd HH:mm:ss"
    ) + " ET";
  } catch (_) {}

  ws.appendRow([
    ts,                         // Submitted At (ET)
    data.firstName  || "",      // First Name
    data.lastName   || "",      // Last Name
    data.language   || "",      // Language
    data.location   || "",      // Location
    s[0], s[1], s[2],           // Star ratings 1–3
    s[3], s[4], s[5],           // Star ratings 4–6
    avg,                        // Average Stars
    data.thoughts   || "",      // Written Thoughts
    data.fillSeconds || ""      // Fill Time (seconds)
  ]);
}


// ── Test function – run manually in Apps Script to verify ─────────────────
function testSubmission() {
  appendRow({
    firstName:   "Test",
    lastName:    "Client",
    language:    "en",
    location:    "Waterbury, CT",
    stars:       [5, 5, 5, 5, 5, 5],
    thoughts:    "Lilian was absolutely wonderful to work with!",
    fillSeconds: 120,
    submittedAt: new Date().toISOString()
  });
  Logger.log("✅ Test row appended — check the Responses sheet!");
}
