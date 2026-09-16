/**
 * app.js — reads the offer form, fills template.pdf's real form fields
 * using FIELD_MAP (see field-map.js), and lets the user preview/download
 * the completed contract. Everything happens in the browser — nothing is
 * uploaded anywhere.
 */

const TEMPLATE_URL = "template.pdf";

function getFormValues() {
  const values = {};
  for (const { formId } of FIELD_MAP) {
    const el = document.getElementById(formId);
    values[formId] = el ? el.value : "";
  }
  return values;
}

function formatValue(raw, type) {
  if (!raw) return "";
  if (type === "currency") {
    const n = Number(raw);
    if (Number.isNaN(n)) return raw;
    return n.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
  }
  if (type === "date") {
    const d = new Date(raw + "T00:00:00");
    if (Number.isNaN(d.getTime())) return raw;
    return d.toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
  }
  return raw;
}

function labelFor(formId) {
  const el = document.querySelector(`label[for="${formId}"]`);
  return el ? el.textContent.trim() : formId;
}

function setStatus(msg, kind) {
  const el = document.getElementById("status");
  el.textContent = msg;
  el.className = kind || "";
}

function buildReviewRows(values) {
  return FIELD_MAP
    .filter(({ formId }) => values[formId])
    .map(({ formId, type }) => {
      const label = labelFor(formId);
      const val = formatValue(values[formId], type);
      return `<tr><td>${label}</td><td>${escapeHtml(val)}</td></tr>`;
    })
    .join("");
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

document.getElementById("reviewBtn").addEventListener("click", () => {
  const values = getFormValues();
  document.getElementById("reviewTable").innerHTML = buildReviewRows(values);
  document.getElementById("reviewCard").classList.remove("hidden");
  document.getElementById("reviewCard").scrollIntoView({ behavior: "smooth" });
});

document.getElementById("closeReviewBtn").addEventListener("click", () => {
  document.getElementById("reviewCard").classList.add("hidden");
});

document.getElementById("offerForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const generateBtn = document.getElementById("generateBtn");
  generateBtn.disabled = true;
  setStatus("Loading contract template...");

  try {
    const { PDFDocument } = PDFLib;

    const templateBytes = await fetch(TEMPLATE_URL).then((res) => {
      if (!res.ok) throw new Error(`Could not load ${TEMPLATE_URL} (${res.status})`);
      return res.arrayBuffer();
    });

    const pdfDoc = await PDFDocument.load(templateBytes);
    const form = pdfDoc.getForm();
    const values = getFormValues();

    const missingFields = [];

    for (const { formId, pdfField, type } of FIELD_MAP) {
      const raw = values[formId];
      if (!raw) continue;
      const text = formatValue(raw, type);
      try {
        const field = form.getTextField(pdfField);
        field.setText(text);
      } catch (err) {
        missingFields.push(pdfField);
      }
    }

    form.flatten({ updateFieldAppearances: true });

    const filledBytes = await pdfDoc.save();
    const blob = new Blob([filledBytes], { type: "application/pdf" });
    const url = URL.createObjectURL(blob);

    const buyer = (values.buyerNames || "offer").replace(/[^a-z0-9]+/gi, "_");
    const filename = `Offer_${buyer}_${new Date().toISOString().slice(0, 10)}.pdf`;

    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();

    window.open(url, "_blank");

    if (missingFields.length) {
      setStatus(
        `Downloaded, but ${missingFields.length} field name(s) in field-map.js didn't match the PDF: ${missingFields.join(", ")}. Open the console and run debugListFields() to see the real names.`,
        "error"
      );
    } else {
      setStatus("Offer PDF generated — review it carefully before sending.", "ok");
    }
  } catch (err) {
    console.error(err);
    setStatus(`Error: ${err.message}`, "error");
  } finally {
    generateBtn.disabled = false;
  }
});

// Debug helper: run debugListFields() in the browser console to print
// every real field name in template.pdf, so field-map.js can be corrected.
window.debugListFields = async function () {
  const { PDFDocument } = PDFLib;
  const templateBytes = await fetch(TEMPLATE_URL).then((r) => r.arrayBuffer());
  const pdfDoc = await PDFDocument.load(templateBytes);
  const form = pdfDoc.getForm();
  const names = form.getFields().map((f) => `${f.constructor.name}: "${f.getName()}"`);
  console.log(names.join("\n"));
  return names;
};
