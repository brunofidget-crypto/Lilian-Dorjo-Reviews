/**
 * field-map.js
 *
 * Maps the offer form's answers to the real AcroForm field names inside
 * template.pdf — SmartMLS "Standard Form Real Estate Contract" (rev 9.24).
 *
 * Field names/positions were confirmed by inspecting the actual PDF's
 * AcroForm fields and cross-referencing their coordinates against the
 * extracted contract text, so these are the real field names, not guesses.
 */

// Simple text/currency/date fields: one form answer -> one PDF text field.
// A single formId may map to more than one PDF field (e.g. the mortgage
// amount in Paragraph 5(c) is the same number as Paragraph 6(a)).
const TEXT_FIELD_MAP = [
  // Parties
  { formId: "sellerNames",        pdfField: "1 Sellers",        type: "text" },
  { formId: "sellerAddress",      pdfField: "Address",          type: "text" },
  { formId: "buyerNames",         pdfField: "2 Buyers",         type: "text" },
  { formId: "buyerAddress",       pdfField: "Address_2",        type: "text" },

  // Property (repeats in the header of pages 2-4 automatically)
  { formId: "propertyAddress",    pdfField: "3Real Property Address", type: "text" },
  { formId: "contractDate",       pdfField: "Page 2 of Real Estate Contract Dated", type: "date" },

  // Personal property
  { formId: "includedItems1",     pdfField: "4Personal Property if any to be included 1", type: "text" },
  { formId: "includedItems2",     pdfField: "4Personal Property if any to be included 2", type: "text" },
  { formId: "excludedItems",      pdfField: "To be excluded",   type: "text" },

  // Paragraph 5 — Purchase Price breakdown
  { formId: "initialDeposit",     pdfField: "undefined_2",      type: "currency" },
  { formId: "additionalDeposit",  pdfField: "undefined_3",      type: "currency" },
  { formId: "additionalDepositDate", pdfField: "b By Additional Deposit to be paid on or before", type: "date" },
  { formId: "mortgageAmount",     pdfField: "undefined_4",      type: "currency" }, // 5(c)
  { formId: "balanceAtClosing",   pdfField: "undefined_5",      type: "currency" }, // 5(d)
  { formId: "totalPurchasePrice", pdfField: "undefined_6",      type: "currency" }, // computed, see app.js

  // Paragraph 6 — Mortgage Financing Contingency
  { formId: "mortgageAmount",     pdfField: "undefined",        type: "currency" }, // 6(a) — same $ as 5(c)
  { formId: "loanCommitmentDate", pdfField: "c Written Loan Commitment to be obtained by", type: "date" },

  // Paragraph 7 — Closing
  { formId: "closingDate",        pdfField: "MonthDayYear",     type: "date" },
  { formId: "closingCounty",      pdfField: "at Sellers attorneys office or at Mortgage Lenders office in", type: "text" },

  // Paragraph 9 — Inspection Contingency
  { formId: "inspectionCompletionDate", pdfField: "9 Inspection ContingencyThe inspections checked below shall be completed not later thanInspection Completion Date", type: "date" },

  // Paragraph 14 — Buyer's Broker fee
  { formId: "brokerFeeAmount",    pdfField: "The Seller agrees to pay the Buyers Broker a fee in the amount of", type: "currency" },
  { formId: "brokerFeePercent",   pdfField: "or",                type: "text" },

  // Paragraphs 15-16
  { formId: "additionalTerms",    pdfField: "15 Additional Terms andor seller concessions 1", type: "text" },
  { formId: "ridersAttached",     pdfField: "16 Riders Attached", type: "text" },

  // Seller's Agent / Attorney
  { formId: "sellersAgentNamePhone", pdfField: "Sellers Agent",  type: "text" },
  { formId: "sellersAgentLicense",   pdfField: "License Number", type: "text" },
  { formId: "sellersAgentFirm",      pdfField: "Agents Firm",    type: "text" },
  { formId: "sellersAgentAddress",   pdfField: "Address_3",      type: "text" },
  { formId: "sellersAttorneyNamePhone", pdfField: "Sellers Attorney", type: "text" },
  { formId: "sellersAttorneyEmail",  pdfField: "Attorneys Email", type: "text" },
  { formId: "sellersAttorneyAddress",pdfField: "Address_5",      type: "text" },

  // Buyer's Agent / Attorney
  { formId: "buyersAgentNamePhone",  pdfField: "Buyers Agent",   type: "text" },
  { formId: "buyersAgentLicense",    pdfField: "License Number_2", type: "text" },
  { formId: "buyersAgentFirm",       pdfField: "Agents Firm_2",  type: "text" },
  { formId: "buyersAgentAddress",    pdfField: "Address_4",      type: "text" },
  { formId: "buyersAttorneyNamePhone", pdfField: "Buyers Attorney", type: "text" },
  { formId: "buyersAttorneyEmail",   pdfField: "Attorneys Email_2", type: "text" },
  { formId: "buyersAttorneyAddress", pdfField: "Address_6",      type: "text" },
];

// Radio-group fields: form select value -> PDF export choice.
const RADIO_FIELD_MAP = [
  {
    formId: "financingType",
    pdfField: "6 finance",
    choices: { thirdParty: "Choice1", purchaseMoney: "Choice2" },
  },
  {
    formId: "agencyDisclosure",
    pdfField: "agents select",
    choices: { dualAgent: "Choice1", sellingAgentIsBuyersAgent: "Choice2", subAgent: "Choice3" },
  },
  // Paragraph 9 inspection items — each is YES (Choice1) / WAIVED (Choice2)
  { formId: "inspect_building",  pdfField: "9a", choices: { yes: "Choice1", waived: "Choice2" } },
  { formId: "inspect_termite",   pdfField: "9b", choices: { yes: "Choice1", waived: "Choice2" } },
  { formId: "inspect_septic",    pdfField: "9c", choices: { yes: "Choice1", waived: "Choice2" } },
  { formId: "inspect_titleSearch", pdfField: "9d", choices: { yes: "Choice1", waived: "Choice2" } },
  { formId: "inspect_water",     pdfField: "9e", choices: { yes: "Choice1", waived: "Choice2" } },
  { formId: "inspect_well",      pdfField: "9f", choices: { yes: "Choice1", waived: "Choice2" } },
  { formId: "inspect_radon",     pdfField: "9g", choices: { yes: "Choice1", waived: "Choice2" } },
  { formId: "inspect_oilTank",   pdfField: "9h", choices: { yes: "Choice1", waived: "Choice2" } },
  { formId: "inspect_lead",      pdfField: "9i", choices: { yes: "Choice1", waived: "Choice2" } },
  { formId: "inspect_asbestos",  pdfField: "9j", choices: { yes: "Choice1", waived: "Choice2" } },
];

// Inspection items shown together in the UI, in the order they appear on
// the form (Paragraph 9's YES/WAIVED grid).
const INSPECTION_ITEMS = [
  { formId: "inspect_building",    label: "Building/Mechanical" },
  { formId: "inspect_termite",     label: "Termite/Other Insects" },
  { formId: "inspect_septic",      label: "Septic" },
  { formId: "inspect_titleSearch", label: "Title Search" },
  { formId: "inspect_water",       label: "Water" },
  { formId: "inspect_well",        label: "Well/Organic Chemicals" },
  { formId: "inspect_radon",       label: "Radon-Air/Water" },
  { formId: "inspect_oilTank",     label: "Oil Tank" },
  { formId: "inspect_lead",        label: "Lead" },
  { formId: "inspect_asbestos",    label: "Asbestos" },
];
