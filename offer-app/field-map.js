/**
 * field-map.js
 *
 * Maps the offer form's answers to the actual field names inside
 * template.pdf (the SmartMLS "Standard Form Real Estate Contract").
 *
 * PLACEHOLDER — the real template.pdf has not been supplied yet, so the
 * PDF_FIELD names below are guesses. Once the real contract PDF is added
 * at offer-app/template.pdf, open the site, click "Debug: list PDF fields"
 * in the browser console (window.debugListFields()), and update the
 * PDF_FIELD value on the right of each mapping to match the real field name.
 */

const FIELD_MAP = [
  // -- Parties --------------------------------------------------------
  { formId: "buyerNames",        pdfField: "Buyer Names",              type: "text" },
  { formId: "sellerNames",       pdfField: "Seller Names",             type: "text" },

  // -- Property ---------------------------------------------------------
  { formId: "propertyAddress",   pdfField: "Property Address",         type: "text" },
  { formId: "propertyTown",      pdfField: "Town",                     type: "text" },
  { formId: "propertyState",     pdfField: "State",                    type: "text" },
  { formId: "propertyZip",       pdfField: "Zip",                      type: "text" },

  // -- Price & deposit ----------------------------------------------------
  { formId: "purchasePrice",     pdfField: "Purchase Price",           type: "currency" },
  { formId: "depositAmount",     pdfField: "Deposit Amount",           type: "currency" },
  { formId: "depositHolder",     pdfField: "Deposit Held By",          type: "text" },

  // -- Financing -----------------------------------------------------------
  { formId: "financingType",     pdfField: "Financing Type",           type: "text" },
  { formId: "mortgageAmount",    pdfField: "Mortgage Amount",          type: "currency" },
  { formId: "mortgageDeadline",  pdfField: "Mortgage Commitment Date", type: "date" },

  // -- Contingencies --------------------------------------------------------
  { formId: "inspectionDeadline",pdfField: "Inspection Contingency Date", type: "date" },
  { formId: "otherContingencies",pdfField: "Other Contingencies",      type: "text" },

  // -- Dates --------------------------------------------------------------
  { formId: "closingDate",       pdfField: "Closing Date",             type: "date" },
  { formId: "possessionDate",    pdfField: "Possession Date",          type: "date" },
  { formId: "offerExpiration",   pdfField: "Offer Expiration Date",    type: "date" },

  // -- Inclusions / exclusions ------------------------------------------------
  { formId: "inclusions",        pdfField: "Included Items",           type: "text" },
  { formId: "exclusions",        pdfField: "Excluded Items",           type: "text" },

  // -- Attorneys ------------------------------------------------------------
  { formId: "buyerAttorney",     pdfField: "Buyer Attorney",           type: "text" },
  { formId: "sellerAttorney",    pdfField: "Seller Attorney",          type: "text" },

  // -- Brokers --------------------------------------------------------------
  { formId: "listingBroker",     pdfField: "Listing Broker",           type: "text" },
  { formId: "sellingBroker",     pdfField: "Selling Broker",           type: "text" },
  { formId: "commissionSplit",   pdfField: "Commission",               type: "text" },

  // -- Misc -----------------------------------------------------------------
  { formId: "specialProvisions", pdfField: "Special Provisions",       type: "text" },
];
