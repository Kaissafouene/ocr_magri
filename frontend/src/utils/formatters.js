/**
 * Format a confidence score as a percentage string.
 * e.g. 0.853 → "85%"
 */
export function formatConfidence(value) {
  if (value === null || value === undefined) return "—";
  return `${Math.round(value * 100)}%`;
}


export function formatCurrency(value, currency = "DT") {
  if (value === null || value === undefined) return "—";
  return `${Number(value).toLocaleString("fr-TN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })} ${currency}`;
}


export function formatQty(value) {
  if (value === null || value === undefined) return "—";
  return Number(value).toLocaleString("fr-TN", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
  });
}


export function formatDate(dateStr) {
  if (!dateStr) return "—";
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString("fr-TN", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
  } catch {
    return dateStr;
  }
}


export function formatExtractionTier(tier) {
  const map = {
    1: "Template",
    2: "Cloud OCR",
    3: "AI Fallback",
    4: "Human",
  };
  return map[tier] || `Tier ${tier}`;
}

/**
 * Format ISO timestamp  local time.
 */
export function formatTimestamp(isoStr) {
  if (!isoStr) return "—";
  return new Date(isoStr).toLocaleString("fr-TN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}