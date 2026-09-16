/**
 * app.js — reads the offer form, fills template.pdf's real form fields
 * using TEXT_FIELD_MAP / RADIO_FIELD_MAP (see field-map.js), and lets the
 * user preview/download the completed contract. Everything happens in the
 * browser — nothing is uploaded anywhere.
 */

const TEMPLATE_URL = "template.pdf";

function buildInspectionGrid() {
  const grid = document.getElementById("inspectionGrid");
  grid.innerHTML = INSPECTION_ITEMS.map(({ formId, label }) => `
    <div class="field row" style="grid-template-columns: 2fr 1fr;">
      <label style="align-self:center;margin:0;">${label}</label>
      <select id="${formId}">
        <option value="">—</option>
        <option value="yes">Required (YES)</option>
        <option value="waived">Waived</option>
      </select>
    </div>
  `).join("");
}
buildInspectionGrid();

function allFormIds() {
  const ids = new Set();
  for (const { formId } of TEXT_FIELD_MAP) ids.add(formId);
  for (const { formId } of RADIO_FIELD_MAP) ids.add(formId);
  return [...ids];
}

function getFormValues() {
  const values = {};
  for (const formId of allFormIds()) {
    const el = document.getElementById(formId);
    values[formId] = el ? el.value : "";
  }
  return values;
}

function currencyNumber(raw) {
  const n = Number(raw);
  return Number.isNaN(n) ? 0 : n;
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

function computeTotal(values) {
  return (
    currencyNumber(values.initialDeposit) +
    currencyNumber(values.additionalDeposit) +
    currencyNumber(values.mortgageAmount) +
    currencyNumber(values.balanceAtClosing)
  );
}

function updateTotalDisplay() {
  const values = getFormValues();
  const total = computeTotal(values);
  document.getElementById("totalPurchasePriceDisplay").value =
    total.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
}

document.querySelectorAll(".price-part").forEach((el) =>
  el.addEventListener("input", updateTotalDisplay)
);

function labelFor(formId) {
  const el = document.querySelector(`label[for="${formId}"]`);
  return el ? el.textContent.trim() : formId;
}

function setStatus(msg, kind) {
  const el = document.getElementById("status");
  el.textContent = msg;
  el.className = kind || "";
}

function buildReviewRows(values, total) {
  const rows = TEXT_FIELD_MAP
    .filter(({ formId }) => values[formId])
    .map(({ formId, type }) => {
      const label = labelFor(formId);
      const val = formatValue(values[formId], type);
      return `<tr><td>${label}</td><td>${escapeHtml(val)}</td></tr>`;
    });
  rows.push(`<tr><td>Total Purchase Price</td><td>${escapeHtml(total.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }))}</td></tr>`);
  for (const { formId } of RADIO_FIELD_MAP) {
    if (values[formId]) {
      rows.push(`<tr><td>${labelFor(formId) || formId}</td><td>${escapeHtml(values[formId])}</td></tr>`);
    }
  }
  return rows.join("");
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

document.getElementById("reviewBtn").addEventListener("click", () => {
  const values = getFormValues();
  document.getElementById("reviewTable").innerHTML = buildReviewRows(values, computeTotal(values));
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
    values.totalPurchasePrice = String(computeTotal(values));

    const problems = [];

    for (const { formId, pdfField, type } of TEXT_FIELD_MAP) {
      const raw = values[formId];
      if (!raw) continue;
      const text = formatValue(raw, type);
      try {
        form.getTextField(pdfField).setText(text);
      } catch (err) {
        problems.push(`text field "${pdfField}" (${err.message})`);
      }
    }

    for (const { formId, pdfField, choices } of RADIO_FIELD_MAP) {
      const raw = values[formId];
      if (!raw) continue;
      const exportValue = choices[raw];
      if (!exportValue) continue;
      try {
        form.getRadioGroup(pdfField).select(exportValue);
      } catch (err) {
        problems.push(`radio group "${pdfField}" (${err.message})`);
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

    if (problems.length) {
      setStatus(`Downloaded, but some fields didn't fill: ${problems.join("; ")}`, "error");
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
// every real field name in template.pdf.
window.debugListFields = async function () {
  const { PDFDocument } = PDFLib;
  const templateBytes = await fetch(TEMPLATE_URL).then((r) => r.arrayBuffer());
  const pdfDoc = await PDFDocument.load(templateBytes);
  const form = pdfDoc.getForm();
  const names = form.getFields().map((f) => `${f.constructor.name}: "${f.getName()}"`);
  console.log(names.join("\n"));
  return names;
};
